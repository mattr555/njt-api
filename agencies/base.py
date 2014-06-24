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
        self.datadir = os.path.join('data', self.__class__.name)
        self.load()
        self.station_replacements = {} #map of commonly-used names for stations to their gtfs stop_names
                                       #only if they're non-obvious ex: 'philadelphia': '30TH ST. PHL.'
        self.normalize_replacements = ['rd ','nd ','st ','th '] #list of parts of names messed up by str.title()
        self.route_whitelist = [] #populate if gtfs data has lines that you don't want 
                                  #(ex: if it has bus data when you only want subway)

    def parse(self):
        """parse the gtfs data into useable json format
        a subclass should generally call this function with super(Agency, self).__init__()
        if this isn't done, you'll have to parse the feed and populate your own dicts and schemas.

        Any files needed to be generated to use realtime apis should be created here. It is suggested
        that you call this parent method first, and then use the data generated to build your other files"""
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
        """load the data from the files
        any new files you generate should be loaded here into their own properties"""
        with open(os.path.join(self.datadir, 'routes')) as f:
            self.routes = json.load(f)
        with open(os.path.join(self.datadir, 'stops')) as f:
            self.stops = json.load(f)
        with open(os.path.join(self.datadir, 'dates')) as f:
            self.dates = json.load(f)

    def normalize_stop_name(self, s):
        """this method takes a stop name (str) and returns a new stop name (str)
        this should fix the errors caused when str.title() is called on a stop name
        this method generally doesn't need to be overwritten, rather self.normalize_replacements
        should be edited."""
        s = s.title()
        for i in self.normalize_replacements:
            if i.title() in s:
                s = s.replace(i.title(), i)
        return s.replace('station', "Station")

    def get_station_page(self, station):
        """this method takes a station name (str) and returns data from an api (any type)
        and a url where a user can find more realtime data (str)
        the data from the api will be passed to get_status() and train_list(), and will hopefully
        be useful there."""
        return '', ''

    def get_status(self, trip, orig, dest, station_page):
        """this method takes a trip dict, an origin (str), a destination (str), and the data
        returned from the api called in get_station_page(). it will return the train's status (str) and
        the track the train will depart from (str)"""
        return '', ''

    def train_list(self, station_page):
        """this method takes the data returned from the realtime api called in get_station_page().
        it will return a list of trains (strs) currently approaching or at the station. If there are late
        trains, the list should include them."""
        return []

    def get_train_identifier(self, trip):
        """this method takes a transitfeed.Trip object and returns the user-identifiable train id (str).
        this number is generally found on timetables. if there is no such number in the system, it should
        return an empty string."""
        return trip.block_id
