from base import Base

class PATH(Base):
    name = 'path'
    
    def __init__(self):
        super(PATH, self).__init__()
        self.station_replacements = {
            'wtc': 'World Trade Center'
        }
