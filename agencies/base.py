import os
import json
import datetime

def toposort2(data):
    """Dependencies are expressed as a dictionary whose keys are items
and whose values are a set of dependent items. Output is a list of
sets in topological order. The first set consists of items with no
dependences, each subsequent set consists of items that depend upon
items in the preceeding sets.

>>> print '\\n'.join(repr(sorted(x)) for x in toposort2({
...     2: set([11]),
...     9: set([11,8]),
...     10: set([11,3]),
...     11: set([7,5]),
...     8: set([7,3]),
...     }) )
[3, 5, 7]
[8, 11]
[2, 9, 10]

stolen from http://code.activestate.com/recipes/578272-topological-sort/

"""

    from functools import reduce

    # Ignore self dependencies.
    for k, v in data.items():
        v.discard(k)
    # Find all items that don't depend on anything.
    extra_items_in_deps = reduce(set.union, data.itervalues()) - set(data.iterkeys())
    # Add empty dependences where needed
    data.update({item: set() for item in extra_items_in_deps})
    while True:
        ordered = set(item for item, dep in data.iteritems() if not dep)
        if not ordered:
            break
        yield ordered
        data = {item: (dep - ordered)
                for item, dep in data.iteritems()
                if item not in ordered}
    assert not data, "Cyclic dependencies exist among these items:\n%s" % '\n'.join(repr(x) for x in data.iteritems())

def stop_dict(s):
    return {'stop_name': s.stop_name, 'stop_id': s.stop_id, 'times': {'0': {}, '1': {}}}

def append_to_list_in_dict(d, key, val, remove=False):
    if remove:
        if d.get(key):
            d[key].remove(val)
        else:
            d[key] = []
    else:
        if d.get(key):
            d[key].append(val)
        else:
            d[key] = [val]

def daterange(start_date, end_date):
    start_date = datetime.datetime.strptime(start_date, '%Y%m%d')
    end_date = datetime.datetime.strptime(end_date, '%Y%m%d')
    for n in range(int((end_date - start_date).days)):
        yield start_date + datetime.timedelta(n)

class Base(object):
    name = ''             # name of the folder where the data is found and name to use in url
    station_replacements = {}  # map of commonly-used names for stations to their gtfs stop_names
                               # only if they're non-obvious ex: 'philadelphia': '30TH ST. PHL.'
    normalize_replacements = ['rd ', 'nd ', 'st ', 'th ']  # list of parts of names messed up by str.title()
    route_whitelist = []  # populate if gtfs data has lines that you don't want
                          # (ex: if it has bus data when you only want subway)
    tzoffset = -5         # timezone offset from UTC (these settings are default for EST)
    dst_observed = True   # is dst observed here?
    timeswitch = 4        # hour when to roll over to the next day

    def __init__(self):
        self.datadir = os.path.join('data', self.__class__.name)
        try:
            self.load()
        except:
            self.routes = {}

    def parse(self, api=False):
        """parse the gtfs data into useable json format
        a subclass should generally call this function with super(Agency, self).__init__()
        if this isn't done, you'll have to parse the feed and populate your own dicts and schemas.

        Any files needed to be generated to use realtime apis should be created here. It is suggested
        that you call this parent method first, and then use the data generated to build your other files"""
        import transitfeed

        # do we have a whitelist?
        wl = bool(self.__class__.route_whitelist)

        # load data into a schedule object
        sched = transitfeed.Loader(os.path.join(self.datadir, 'gtfs.zip')).Load()
        routes = {}
        route_graph = {}

        # populate our route dictionaries
        for route in sched.GetRouteList():
            if not wl or (wl and route.route_id in self.__class__.route_whitelist):  # filter whitelist
                routes[route.route_id] = {'name': route.route_long_name, 'route': []}
                route_graph[route.route_id] = {}

        # build our trip graph
        # map of stop_id to set of next stop_ids
        for trip in sched.GetTripList():
            if trip.route_id in routes:
                pattern = list(trip.GetPattern())
                if trip.direction_id == '1':
                    pattern.reverse()  # only get stops going one way
                d = route_graph[trip.route_id]
                for i in range(len(pattern)-1):  # don't do the last stop, it has no outgoing edge
                    if d.get(pattern[i]['stop_id']):
                        d[pattern[i]['stop_id']].add(pattern[i+1]['stop_id'])
                    else:
                        d[pattern[i]['stop_id']] = set([pattern[i+1]['stop_id']])

        # build a list of stop_ids in order, then create the stop dicts
        for route_id, stops in route_graph.iteritems():
            l = []
            for i in toposort2(stops):  # topological sort the graph to determine the order
                l += i
            routes[route_id]['route'] = [stop_dict(sched.GetStop(i)) for i in reversed(l)]

        # add the times
        for trip in sched.GetTripList():  # every trip
            if trip.route_id in routes:
                times = trip.GetStopTimesTuples()
                route = routes[trip.route_id]['route']
                dir_id = str(trip.direction_id)
                serv_id = str(trip.service_id)
                for time in times:  # each stop on the trip
                    stop_id = time[3]
                    for stop in route:  # look through every stop on route to find this stop
                        if not stop['times'][dir_id].get(trip.service_id):
                            stop['times'][dir_id][serv_id] = []
                        if stop['stop_id'] == stop_id:
                            # arrival time, trip id, train id
                            stop['times'][dir_id][serv_id].append((time[1], time[0], self.get_train_identifier(trip)))
                            break  # we're done with this current stop, no need to loop through rest

        with open(os.path.join(self.datadir, 'routes'), 'w') as f:
            json.dump(routes, f)

        # map of stop name: routes it serves
        stops = {}
        for k, v in routes.items():
            for stop in v['route']:
                append_to_list_in_dict(stops, stop['stop_name'], k)

        with open(os.path.join(self.datadir, 'stops'), 'w') as f:
            json.dump(stops, f)

        # map of each day: applicable serivice periods
        dates = {}
        for sp in sched.GetServicePeriodList():
            if sp.start_date:  # this is a service period with a range of dates and weekdays defined
                for date in daterange(sp.start_date, sp.end_date):
                    if sp.day_of_week[date.weekday()]:  # add each day to the dict if its weekday is serviced
                        d = date.strftime('%Y%m%d')
                        append_to_list_in_dict(dates, d, sp.service_id)

            for (id, date, extype) in sp.GetCalendarDatesFieldValuesTuples():  # special days
                if extype == '1':  # add the day
                    append_to_list_in_dict(dates, date, id)
                else:  # remove the day
                    append_to_list_in_dict(dates, date, id, remove=True)

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
        this method generally doesn't need to be overwritten, rather class attrib. normalize_replacements
        should be edited."""
        s = s.title()
        for i in self.__class__.normalize_replacements:
            if i.title() in s:
                s = s.replace(i.title(), i)
        return s.replace('station', "Station")

    def fix_pair(self, orig, dest):
        """perform any special case handling here"""
        return orig, dest

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
