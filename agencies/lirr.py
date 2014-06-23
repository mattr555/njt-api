from base import Base

class LIRR(Base):
    def __init__(self):
        self.name = 'lirr'
        super(LIRR, self).__init__()

    def get_train_identifier(self, trip):
        return trip.trip_short_name
