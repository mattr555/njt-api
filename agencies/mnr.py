from base import Base

class MetroNorth(Base):
    name = 'mnr'
    
    def get_train_identifier(self, trip):
        return trip.trip_short_name
