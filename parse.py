from util import iter_agencies, avail_agencies
import sys
import os
import argparse
import importlib
from agencies.base import Base

sys.path.append(os.path.join(os.path.dirname(__file__), 'lib'))

parser = argparse.ArgumentParser()
parser.add_argument('agencies', type=str, nargs='*', default=[], help="list of agencies to parse (default all)")
parser.add_argument('--api', help="reload realtime api data?", action="store_true")
args = parser.parse_args()

def parse_agency(agency):
    print 'starting', agency.name
    agency().parse(args.api)
    print agency.name, 'parsed!'

if args.agencies:
    avail = avail_agencies()
    for name in args.agencies:
        if name in avail:
            importlib.import_module('agencies.' + name)
    for agency in Base.__subclasses__():
        parse_agency(agency)
else:
    for agency in iter_agencies():
        parse_agency(agency)
