import datetime
import sys
import os
from util import iter_agencies, AmericanTimezone, norm_hour

def find_stop(s, stops, station_replacements):
    """parse stop list to find a stop"""
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
        return str(matches[0])  # if there is only one match, return it
    return list(map(str, matches))  # a list of the matches

def infer_stop(known, unknown, stops):
    """figure out the stop based on the other's route"""
    known_routes = set(stops[known])
    unknown_routes = []
    for i in unknown:
        unknown_routes.append(set(stops[i]))
    for stop, iroutes in zip(unknown, unknown_routes):
        if known_routes.intersection(iroutes):  # if the matched stop shares a line, return the stop
            return stop, list(known_routes.intersection(iroutes))
    return None, None


def get_times_response(agency, orig, dest):
    # set variables we need
    orig = orig.replace('-', ' ')
    dest = dest.replace('-', ' ')
    nowt = datetime.datetime.now(AmericanTimezone(agency.tzoffset, agency.dst_observed))
    now = nowt.strftime('%H:%M:%S')
    if nowt.hour < agency.timeswitch:  # use the previous day's schedule if it is the early morning
        nowt -= datetime.timedelta(days=1)
    today = nowt.strftime('%Y%m%d')
    route_matches = []
    resp = {'failed': True, 'routes': [], 'now': now}  # default of the response object

    # find the stop names
    orig_eq = find_stop(orig, agency.stops, agency.station_replacements)
    dest_eq = find_stop(dest, agency.stops, agency.station_replacements)

    orig_eq, dest_eq = agency.fix_pair(orig_eq, dest_eq)

    # if they're both definite stops, find the routes that service both
    if (type(orig_eq) is str) and (type(dest_eq) is str):
        orig = orig_eq
        dest = dest_eq
        orig_routes = set(agency.stops[orig])
        dest_routes = set(agency.stops[dest])
        route_matches = list(orig_routes.intersection(dest_routes))
    # else, figure out which stop they meant by looking at the other's route
    elif type(orig_eq) is list and type(dest_eq) is str:
        dest = dest_eq
        orig, route_matches = infer_stop(dest, orig_eq, agency.stops)
    elif type(dest_eq) is list and type(orig_eq) is str:
        orig = orig_eq
        dest, route_matches = infer_stop(orig, dest_eq, agency.stops)

    # look through each route and find the trains that go there
    if route_matches:
        # get the realtime data
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
                if orig_times.get(i) and dest_times.get(i):
                    orig_real_times += orig_times[i]
                    dest_real_times += dest_times[i]

            orig_real_times.sort()
            dest_real_times.sort()

            # get the next 3 trains for each route
            train_count = 0
            while train_count < 3:
                dep_time, dep_trip, dep_train, arr_time = (None,)*4
                for i in range(len(orig_real_times)):
                    time, trip, train = orig_real_times.pop(0)
                    time = norm_hour(time)
                    if now < time or train in status_page_trains:  # see if the train is delayed
                        dep_time = time
                        dep_trip = trip
                        dep_train = train
                        break
                for i, j, _ in dest_real_times:
                    if j == dep_trip:  # make sure the train actually stops on this trip
                        arr_time = i
                if arr_time:
                    # update the response object
                    resp['origin'] = agency.normalize_stop_name(orig)
                    resp['destination'] = agency.normalize_stop_name(dest)
                    resp['failed'] = False
                    resp['url'] = station_url
                    trip = {'line': route['name'], 'departure_time': dep_time,
                            'arrival_time': arr_time, 'train': dep_train}
                    # get the status and track num from the data
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

sys.path.append(os.path.join(os.path.dirname(__file__), 'lib'))
import bottle

@bottle.route('/')
def index():
    return '''This api is meant for DDG, but you can use it too...<br/>
        endpoint is /:agency/times/:orig/:dest, delimit spaces with -'''

#load our agencies but don't instantiate them (to save resources)
agencies = {}
for agency in iter_agencies():
    agencies[agency.name] = agency

#instantiate an agency if it exists
def get_agency(name):
    agency = agencies.get(name)
    if agency:
        if type(agency) is type:
            agency = agency()
            agencies[agency.name] = agency
        if agency.routes:
            return agency
    return None

@bottle.route('/:agency/times/:orig/:dest')
def times_handler(agency, orig, dest):
    agency = get_agency(agency)
    if agency:
        return get_times_response(agency, orig, dest)
    raise bottle.HTTPError(404)

@bottle.route('/:agency/stops')
def stops_handler(agency):
    agency = get_agency(agency)
    if agency:
        return '\r\n'.join(agency.stops.keys() + agency.station_replacements.keys())
    raise bottle.HTTPError(404)

bottle.debug(True)
bottle.run(server='gae')
application = bottle.app()
