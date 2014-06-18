import transitfeed
import json
import csv
import sys

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

sched = transitfeed.Loader('rail_data.zip').Load()
routes = {}
for route in sched.GetRouteList():
	routes[route.route_id] = {'name': route.route_long_name, 'route': []}

for trip in sched.GetTripList():
	pattern = list(trip.GetPattern())
	if trip.direction_id == '1':
		pattern.reverse()
	pattern = parse_pattern(pattern)
	if routes[trip.route_id]['route'] != pattern:
		routes[trip.route_id]['route'] = merge_patterns(routes[trip.route_id]['route'], pattern)

for trip in sched.GetTripList():
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
				stop['times'][dir_id][serv_id].append((time[1], time[0], trip.block_id))

with open('routes', 'w') as f:
	json.dump(routes, f)

stops = {}
for k, v in routes.items():
	for stop in v['route']:
		if stops.get(stop['stop_name']):
			stops[stop['stop_name']].append(k)
		else:
			stops[stop['stop_name']] = [k]

with open('stops', 'w') as f:
	json.dump(stops, f)

dates = {}
for sp in sched.GetServicePeriodList():
	for (id, date, _) in sp.GetCalendarDatesFieldValuesTuples():
		if dates.get(date):
			dates[date].append(id)
		else:
			dates[date] = [id]

with open('dates', 'w') as f:
	json.dump(dates, f)

if '-dv' in sys.argv:
	departurevision = {}
	with open('departurevision.csv') as f:
		for station, code in csv.reader(f):
			matches = []
			done = False
			for k in stops:
				if station.lower() == k.lower():
					departurevision[k] = code
					done = True
					break
				elif station.lower() in k.lower():
					matches.append(k)
			if not done:
				if matches:
					print 'Multiple found for', station, code
					for i, j in enumerate(matches):
						print i, j
					departurevision[matches[int(raw_input('? '))]] = code
				else:
					print 'None found for', station, code
					departurevision[raw_input('? ')] = code

	with open('dv', 'w') as f:
		json.dump(departurevision, f)

print 'parsed!'
