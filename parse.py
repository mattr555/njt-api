from util import iter_agencies
import sys

for agency in iter_agencies():
    print 'starting', agency.name
    agency().parse('-api' in sys.argv)
    print agency.name, 'parsed!'
