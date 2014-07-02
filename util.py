import os
import importlib
from agencies.base import Base

def import_agencies():
    for file in os.listdir('agencies'):
        name, ext = os.path.splitext(file)
        if name in ['base', '__init__']:
            continue
        if ext == os.extsep + 'py':
            importlib.import_module('agencies.' + name)

def iter_agencies():
    import_agencies()
    for i in Base.__subclasses__():
        yield i