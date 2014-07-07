import os
import importlib
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