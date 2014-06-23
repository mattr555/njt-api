from base import Base

class PATH(Base):
    def __init__(self):
        self.name = 'path'
        super(PATH, self).__init__()
        self.station_replacements = {
            'wtc': 'World Trade Center'
        }
