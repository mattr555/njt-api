from base import Base
from keys import wmata as key
import json
import urllib2
import os

class WMATA(Base):
    name = 'wmata'
    
    def __init__(self):
        super(WMATA, self).__init__()
        self.route_whitelist = ["BLUE", "RED", "ORANGE", "GREEN", "YELLOW"]
        self.line_shortcodes = {
            "Metrorail Green Line": "GR",
            "Metrorail Blue Line": "BL",
            "Metrorail Orange Line": "OR",
            "Metrorail Red Line": "RD",
            "Metrorail Yellow Line": "YL"
        }

    def parse(self, api=False):
        super(WMATA, self).parse()
        if api:
            resp = urllib2.urlopen('http://api.wmata.com/Rail.svc/json/jStations?api_key=' + key).read()
            resp = json.loads(resp)["Stations"]
            stations = {}
            apicode = {}
            for i in resp:
                stations[i['Name']] = i['Code']

            for station, code in stations.items():
                matches = []
                for k in self.stops:
                    if station.lower() == k.lower():
                        apicode[k] = code
                        break
                    elif station.lower() in k.lower():
                        matches.append(k)
                else:
                    if len(matches) == 1:
                        apicode[matches[0]] = code
                    elif matches:
                        print 'Multiple found for', station, code
                        for i, j in enumerate(matches):
                            print i, j
                        apicode[matches[int(raw_input('? '))]] = code
                    else:
                        print 'None found for', station, code
                        apicode[raw_input('? ')] = code

            with open(os.path.join(self.datadir, 'apicode'), 'w') as f:
                json.dump(apicode, f)

            self.apicode = apicode

        apicode_routes = {}
        for _, route in self.routes.items():
            apicode_routes[route['name']] = [self.apicode[x['stop_name']] for x in route['route'] if self.apicode.get(x['stop_name'])]

        with open(os.path.join(self.datadir, 'apicode_routes'), 'w') as f:
            json.dump(apicode_routes, f)
        self.apicode_routes = apicode_routes

    def load(self):
        super(WMATA, self).load()
        with open(os.path.join(self.datadir, 'apicode')) as f:
            self.apicode = json.load(f)
        with open(os.path.join(self.datadir, 'apicode_routes')) as f:
            self.apicode_routes = json.load(f)

    def get_station_page(self, station):
        code = self.apicode.get(station)
        if not code:
            return None, None
        url = 'http://api.wmata.com/StationPrediction.svc/json/GetPrediction/{}?api_key={}'.format(code, key)
        return json.loads(urllib2.urlopen(url).read()), 'http://www.wmata.com/rider_tools/tripplanner/tripplanner_form_solo.cfm'

    def get_status(self, trip, orig, dest, status_page):
        line = self.apicode_routes[trip['line']]
        line_code = self.line_shortcodes[trip['line']]
        orig_index = line.index(self.apicode.get(orig))
        dest_index = line.index(self.apicode.get(dest))
        matches = []
        track = ''
        for train in status_page['Trains']:
            if train['DestinationCode'] in line:
                terminus_index = line.index(train['DestinationCode'])
                if (((orig_index - dest_index > 0) and dest_index <= terminus_index) or
                    ((orig_index - dest_index < 0) and dest_index >= terminus_index)) and train['Line'] == line_code:
                    track = train['Group']
                    matches.append(train['Min'])
        return matches, track
