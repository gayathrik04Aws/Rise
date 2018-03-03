from factory.django import DjangoModelFactory


class ReservationFactory(DjangoModelFactory):
    class Meta:
        model = 'reservations.Reservation'


class FlightReservationFactory(DjangoModelFactory):
    class Meta:
        model = 'reservations.FlightReservation'
