import os
import importlib
import datetime
from agencies.base import Base

def avail_agencies():
    l = []
    for file in os.listdir('agencies'):
        name, ext = os.path.splitext(file)
        if name in ['base', '__init__']:
            continue
        if ext == os.extsep + 'py':
            l.append(name)
    return l

def import_agencies():
    for name in avail_agencies():
        importlib.import_module('agencies.' + name)

def iter_agencies():
    import_agencies()
    for i in Base.__subclasses__():
        yield i

def nth(year, month, n, weekday):
    for i in range(((n-1)*7+1), n*7+1):
        date = datetime.datetime(year, month, i, hour=2)
        if date.weekday() == weekday:
            return date

class AmericanTimezone(datetime.tzinfo):
    def __init__(self, offset, dst_observed):
        self.offset = offset
        self.dst_observed = dst_observed
    def dst(self, dt):
        if self.dst_observed:
            dston = nth(dt.year, 3, 2, 6)
            dstoff = nth(dt.year, 11, 1, 6)
            if dston <= dt.replace(tzinfo=None) < dstoff:
                return datetime.timedelta(hours=1)
        return datetime.timedelta(0)
    def utcoffset(self, dt):
        return datetime.timedelta(hours=self.offset) + self.dst(dt)
    def tzname(self, dt):
        return str(self.offset * 100)