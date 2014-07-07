import bottle
import datetime
import json
import logging
from agencies.base import Base
from util import iter_agencies

def nth(year, month, n, weekday):
    for i in range(((n-1)*7+1), n*7+1):
        date = datetime.datetime(year, month, i, hour=2)
        if date.weekday() == weekday:
            return date

class EDT(datetime.tzinfo):
    def dst(self, dt):
        dston = nth(dt.year, 3, 2, 6)
        dstoff = nth(dt.year, 11, 1, 6)
        if dston <= dt.replace(tzinfo=None) < dstoff:
            return datetime.timedelta(hours=1)
        return datetime.timedelta(0)
    def utcoffset(self, dt):
        return datetime.timedelta(hours=-5) + self.dst(dt)
    def tzname(self, dt):
        return "America/New York"

def find_stop(s, stops, station_replacements):
    s = s.lower()
    if s in station_replacements:
        return station_replacements[s]
    matches = []
    for k in stops:
        if s == k.lower():
            return str(k)
        elif s in k.lower():
            matches.append(k)
    if len(matches) == 1:
        return str(matches[0])
    return list(map(str, matches))

def infer_stop(known, unknown, stops):
    known_routes = set(stops[known])
    unknown_routes = []
    for i in unknown:
        unknown_routes.append(set(stops[i]))
    for stop, iroutes in zip(unknown, unknown_routes):
        if known_routes.intersection(iroutes):
            return stop, list(known_routes.intersection(iroutes))
    return None, None


def get_times_response(agency, orig, dest):
    # step 1: figure out which stop they meant
    orig = orig.replace('-', ' ')
    dest = dest.replace('-', ' ')
    nowt = datetime.datetime.now(EDT())
    now = nowt.strftime('%H:%M:%S')
    if nowt.hour < 4:
        nowt -= datetime.timedelta(days=1)
    today = nowt.strftime('%Y%m%d')
    route_matches, trains = [], []
    resp = {'failed': True, 'routes': []}
        
    orig_eq = find_stop(orig, agency.stops, agency.station_replacements)
    dest_eq = find_stop(dest, agency.stops, agency.station_replacements)

    if (type(orig_eq) is str) and (type(dest_eq) is str):
        orig = orig_eq
        dest = dest_eq
        orig_routes = set(agency.stops[orig])
        dest_routes = set(agency.stops[dest])
        route_matches = list(orig_routes.intersection(dest_routes))
    elif type(orig_eq) is list and type(dest_eq) is str:
        dest = dest_eq
        orig, route_matches = infer_stop(dest, orig_eq, agency.stops)
    elif type(dest_eq) is list and type(orig_eq) is str:
        orig = orig_eq
        dest, route_matches = infer_stop(orig, dest_eq, agency.stops)

    # step 2: look through each route and find the trains that go there
    if route_matches:
        status_page, station_url = agency.get_station_page(orig)
        status_page_trains = agency.train_list(status_page) if status_page else []
        for route in route_matches:
            # get the stop times given the direction
            route = agency.routes[route]
            direction = None
            for i in route['route']:
                if i['stop_name'] == orig:
                    if not direction:
                        direction = '0'
                    orig_times = i['times'][direction]
                elif i['stop_name'] == dest:
                    if not direction:
                        direction = '1'
                    dest_times = i['times'][direction]

            # filter the times for the given day
            periods = agency.dates[today]
            orig_real_times = []
            dest_real_times = []
            for i in periods:
                if orig_times.get(i):
                    orig_real_times += orig_times[i]
                    dest_real_times += dest_times[i]

            orig_real_times.sort()
            dest_real_times.sort()

            # get the next 3 trains for each route
            train_count = 0
            while train_count < 3:
                dep_time, dep_trip, arr_time, dep_train = (None,)*4
                for i in range(len(orig_real_times)):
                    time, trip, train = orig_real_times.pop(0)
                    if now < time or train in status_page_trains: #see if the train is delayed
                        dep_time = time
                        dep_trip = trip
                        dep_train = train
                        trains.append(train)
                        break
                for i, j, _ in dest_real_times:
                    if j == dep_trip: #make sure the train actually stops on this trip
                        arr_time = i
                if arr_time:
                    resp['origin'] = agency.normalize_stop_name(orig)
                    resp['destination'] = agency.normalize_stop_name(dest)
                    resp['failed'] = False
                    resp['url'] = station_url
                    trip = {'line': route['name'], 'departure_time': dep_time, 
                            'arrival_time': arr_time, 'train': dep_train}
                    status, track = agency.get_status(trip, orig, dest, status_page) if status_page else ('', '')
                    if type(status) is str:
                        trip['status'] = status.title()
                    elif type(status) is list:
                        trip['status'] = status[train_count] if train_count < len(status) else ''
                    trip['track'] = track
                    resp['routes'].append(trip)
                    train_count += 1
                if not orig_real_times:
                    break

    return resp

@bottle.route('/')
def index():
    return 'This api is meant for DDG, but you can use it too...<br/>endpoint is /times/:from/:to, delimit spaces with -'

def create_times_handler(agency):
    @bottle.route('/{}/times/:orig/:dest'.format(agency.name))
    def handler(orig, dest):
        return get_times_response(agency, orig, dest)
    return handler

def create_stops_handler(agency):
    @bottle.route('/{}/times/:orig/:dest'.format(agency.name))
    def handler(orig, dest):
        return '\r\n'.join(agency.stops.keys() + agency.station_replacements.keys())
    return handler

for agency in iter_agencies():
    instance = agency()
    create_stops_handler(instance)
    create_times_handler(instance)

bottle.run(server='gae')
application = bottle.app()
