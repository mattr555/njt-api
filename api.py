import webapp2
from data import routes, stops, dates, departurevision, station_replacements
import datetime
import json
import lxml.html
import urllib2
import logging

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

class Handler(webapp2.RequestHandler):
    def write(self, *a, **kw):
        self.response.write(*a, **kw)

def get_station_page(station):
	station = departurevision.get(station)
	if not station:
		return None, None
	url = 'http://dv.njtransit.com/mobile/tid-mobile.aspx?sid=' + station
	return urllib2.urlopen(url).read(), url

def get_status(train, station_page):
	h = lxml.html.document_fromstring(station_page)
	t = h.get_element_by_id('GridView1')
	for row in t.getchildren()[1:]:
		data = row.getchildren()[0].getchildren()[1].getchildren()[0].getchildren() #fuckin njt
		if train.lstrip('0') == data[4].text_content().strip():
			return data[5].text_content().strip(), data[2].text_content().strip()
	return '', ''

def train_list(station_page):
	h = lxml.html.document_fromstring(station_page)
	t = h.get_element_by_id('GridView1')
	l = []
	for row in t.getchildren()[1:]:
		data = row.getchildren()[0].getchildren()[1].getchildren()[0].getchildren() #fuckin njt
		l.append(data[4].text_content().strip())
	return l

def find_stop(s):
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

def infer_stop(known, unknown):
	known_routes = set(stops[known])
	unknown_routes = []
	for i in unknown:
		unknown_routes.append(set(stops[i]))
	for stop, iroutes in zip(unknown, unknown_routes):
		if known_routes.intersection(iroutes):
			return stop, list(known_routes.intersection(iroutes))
	return None, None

def normalize_stop_name(s):
	replacements = ["HBLR", "DvLR", "th", "st", "nd", "MSU"]
	s = s.title()
	for i in replacements:
		if i.title() in s:
			s = s.replace(i.title(), i)
	return s.replace('station', "Station")

class MainPage(Handler):
	def get(self):
		self.write('This api is meant for DDG, but you can use it too...\r\nendpoint is /times/:from/:to, delimit spaces with -')

class Times(Handler):
	def get(self, orig, dest):
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
		
		orig_eq = find_stop(orig)
		dest_eq = find_stop(dest)

		if (type(orig_eq) is str) and (type(dest_eq) is str):
			orig = orig_eq
			dest = dest_eq
			orig_routes = set(stops[orig])
			dest_routes = set(stops[dest])
			route_matches = list(orig_routes.intersection(dest_routes))
		elif type(orig_eq) is list and type(dest_eq) is str:
			dest = dest_eq
			orig, route_matches = infer_stop(dest, orig_eq)
		elif type(dest_eq) is list and type(orig_eq) is str:
			orig = orig_eq
			dest, route_matches = infer_stop(orig, dest_eq)

		# step 2: look through each route and find the trains that go there
		if route_matches:
			status_page, station_url = get_station_page(orig)
			status_page_trains = train_list(status_page) if status_page else []
			for route in route_matches:
				# get the stop times given the direction
				route = routes[route]
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
				periods = dates[today]
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
						resp['origin'] = normalize_stop_name(orig)
						resp['destination'] = normalize_stop_name(dest)
						resp['failed'] = False
						resp['url'] = station_url
						status, track = get_status(dep_train, status_page) if status_page else ('', '')
						resp['routes'].append({'line': route['name'], 'departure_time': dep_time, 
							'arrival_time': arr_time, 'train': dep_train, 'status': status.title(), 'track': track})
						train_count += 1
					if not orig_real_times:
						break

		self.response.headers.add_header('Content-Type', 'application/json')
		self.write(json.dumps(resp))

class Stops(Handler):
	def get(self):
		self.response.headers.add_header('Content-Type', 'text/plain')
		self.write('\r\n'.join(stops.keys() + station_replacements.keys()))

application = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/times/([\w-]+)/([\w-]+)', Times),
    ('/stops', Stops)
], debug=True)
