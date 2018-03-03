import factory
from factory.django import DjangoModelFactory
import arrow


class AirportFactory(DjangoModelFactory):
    class Meta:
        model = 'flights.Airport'

    name = factory.Sequence(lambda n: 'Airport %d' % n)


class FlightFactory(DjangoModelFactory):
    class Meta:
        model = 'flights.Flight'

    origin = factory.SubFactory(AirportFactory)
    destination = factory.SubFactory(AirportFactory)
    departure = arrow.now().datetime
    arrival = arrow.now().replace(hours=+1).datetime
    duration = 60


class FlightPlanRestrictionFactory(DjangoModelFactory):
    class Meta:
        model = 'flights.FlightPlanRestriction'


class FlightPlanSeatRestrictionFactory(DjangoModelFactory):
    class Meta:
        model = 'flights.FlightPlanSeatRestriction'
