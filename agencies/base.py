import os
import json
import datetime

def parse_pattern(pattern):
    route = [{'stop_name': s.stop_name, 'stop_id': s.stop_id, 'times': {'0': {}, '1':{}}} for s in pattern]
    return route

def merge_patterns(p1, p2):
    l = list(p2)
    index = 0
    for i in p1:
        if i in l:
            index = l.index(i)
        else:
            l.insert(index, i)
    return l

def daterange(start_date, end_date):
    start_date = datetime.datetime.strptime(start_date, '%Y%m%d')
    end_date = datetime.datetime.strptime(end_date, '%Y%m%d')
    for n in range(int((end_date - start_date).days)):
        yield start_date + datetime.timedelta(n)

class Base(object):
    def __init__(self):
        self.datadir = os.path.join('data', self.name)
        self.load()
        self.station_replacements = {}
        self.normalize_replacements = ['th','nd','st']
        self.route_whitelist = []

    def parse(self):
        import transitfeed

        wl = bool(self.route_whitelist)

        sched = transitfeed.Loader(os.path.join(self.datadir, 'gtfs.zip')).Load()
        routes = {}
        for route in sched.GetRouteList():
            if not wl or (wl and route.route_id in self.route_whitelist):
                routes[route.route_id] = {'name': route.route_long_name, 'route': []}

        for trip in sched.GetTripList():
            if not wl or (wl and trip.route_id in self.route_whitelist):
                pattern = list(trip.GetPattern())
                if trip.direction_id == '1':
                    pattern.reverse()
                pattern = parse_pattern(pattern)
                if routes[trip.route_id]['route'] != pattern:
                    routes[trip.route_id]['route'] = merge_patterns(routes[trip.route_id]['route'], pattern)

        for trip in sched.GetTripList():
            if not wl or (wl and trip.route_id in self.route_whitelist):
                times = trip.GetStopTimesTuples()
                route = routes[trip.route_id]['route']
                dir_id = str(trip.direction_id)
                serv_id = str(trip.service_id)
                for time in times:
                    stop_id = time[3]
                    for stop in route:
                        if not stop['times'][dir_id].get(trip.service_id):
                            stop['times'][dir_id][serv_id] = []
                        if stop['stop_id'] == stop_id:
                            stop['times'][dir_id][serv_id].append((time[1], time[0], self.get_train_identifier(trip)))

        with open(os.path.join(self.datadir, 'routes'), 'w') as f:
            json.dump(routes, f)

        stops = {}
        for k, v in routes.items():
            for stop in v['route']:
                if stops.get(stop['stop_name']):
                    stops[stop['stop_name']].append(k)
                else:
                    stops[stop['stop_name']] = [k]

        with open(os.path.join(self.datadir, 'stops'), 'w') as f:
            json.dump(stops, f)

        dates = {}
        for sp in sched.GetServicePeriodList():
            if sp.start_date:
                for date in daterange(sp.start_date, sp.end_date):
                    if sp.day_of_week[date.weekday()]:
                        d = date.strftime('%Y%m%d')
                        if dates.get(d):
                            dates[d].append(sp.service_id)
                        else:
                            dates[d] = [sp.service_id]
            for (id, date, extype) in sp.GetCalendarDatesFieldValuesTuples():
                if extype == '1':
                    if dates.get(date):
                        dates[date].append(id)
                    else:
                        dates[date] = [id]
                else:
                    if dates.get(date):
                        dates[date].remove(id)
                    else:
                        dates[date] = []

        with open(os.path.join(self.datadir, 'dates'), 'w') as f:
            json.dump(dates, f)

        self.routes = routes
        self.stops = stops
        self.dates = dates

    def load(self):
        with open(os.path.join(self.datadir, 'routes')) as f:
            self.routes = json.load(f)
        with open(os.path.join(self.datadir, 'stops')) as f:
            self.stops = json.load(f)
        with open(os.path.join(self.datadir, 'dates')) as f:
            self.dates = json.load(f)

    def normalize_stop_name(self, s):
        s = s.title()
        for i in self.normalize_replacements:
            if i.title() in s:
                s = s.replace(i.title(), i)
        return s.replace('station', "Station")

    def get_station_page(self, station):
        return '', ''

    def get_status(self, trip, orig, dest, station_page):
        return '', ''

    def train_list(self, station_page):
        return []

    def get_train_identifier(self, trip):
        return trip.block_id