from base import Base

class PATH(Base):
    name = 'path'
    station_replacements = {
        'wtc': 'World Trade Center',
        'jsq': 'Journal Square',
        'nwk': 'Newark Penn Station'
    }
    timeswitch = 0
