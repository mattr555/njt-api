from agencies.njt import NJT
from agencies.wmata import WMATA
import sys

print 'starting NJT'
NJT().parse('-dv' in sys.argv)
print 'NJT complete'

print 'starting WMATA'
WMATA().parse('-wm' in sys.argv)
print 'WMATA complete'
