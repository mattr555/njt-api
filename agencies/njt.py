from base import Base
import os
import json
import urllib2
import lxml.html

class NJT(Base):
	def __init__(self):
		self.name = 'njt'
		super(NJT, self).__init__()
		self.station_replacements = {
			"princeton junction": "PRINCETON JCT.",
			"philadelphia": "30TH ST. PHL.",
			"montclair state university": "MSU",
			"montclair state": "MSU",
			"jersey ave": "JERSEY AVE."
		}
		self.normalize_replacements = ["HBLR", "DvLR", "th", "st", "nd", "MSU"]

	def parse(self, depvision=False):
		import csv

		super(NJT, self).parse()
		if depvision:
			departurevision = {}
			with open(os.path.join(self.datadir, 'departurevision.csv')) as f:
				for station, code in csv.reader(f):
					matches = []
					for k in self.stops:
						if station.lower() == k.lower():
							departurevision[k] = code
							break
						elif station.lower() in k.lower():
							matches.append(k)
					else:
						if len(matches) == 1:
							departurevision[matches[0]] = code
						elif matches:
							print 'Multiple found for', station, code
							for i, j in enumerate(matches):
								print i, j
							departurevision[matches[int(raw_input('? '))]] = code
						else:
							print 'None found for', station, code
							departurevision[raw_input('? ')] = code

			with open(os.path.join(self.datadir, 'dv'), 'w') as f:
				json.dump(departurevision, f)

			self.departurevision = departurevision

	def load(self):
		super(NJT, self).load()
		with open(os.path.join(self.datadir, 'dv')) as f:
			self.departurevision = json.load(f)

	def get_station_page(self, station):
		station = self.departurevision.get(station)
		if not station:
			return None, None
		url = 'http://dv.njtransit.com/mobile/tid-mobile.aspx?sid=' + station
		return urllib2.urlopen(url).read(), url

	def _get_departure_rows(self, station_page):
		h = lxml.html.document_fromstring(station_page)
		t = h.get_element_by_id('GridView1')
		for row in t.getchildren()[1:]:
			data = row.getchildren()[0].getchildren()[1].getchildren()[0].getchildren() #fuckin njt
			yield data

	def get_status(self, trip, orig, dest, station_page):
		for data in self._get_departure_rows(station_page):
			if trip['train'].lstrip('0') == data[4].text_content().strip():
				return data[5].text_content().strip(), data[2].text_content().strip()
		return '', ''

	def train_list(self, station_page):
		l = []
		for data in self._get_departure_rows(station_page):
			l.append(data[4].text_content().strip())
		return l
