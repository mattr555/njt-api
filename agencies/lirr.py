from base import Base

class LIRR(Base):
    name = 'lirr'

    def get_train_identifier(self, trip):
        return trip.trip_short_name
