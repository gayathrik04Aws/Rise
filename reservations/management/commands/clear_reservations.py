from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from reservations.models import Reservation, FlightReservation


class Command(BaseCommand):
    help = 'Cancels expired pending reservations'

    def handle(self, *args, **options):
        now = timezone.now()
        timeout = now - timedelta(seconds=Reservation.TIMEOUT)
        reservations = Reservation.objects.filter(status=Reservation.STATUS_PENDING, expires__lte=now)
        for reservation in reservations:
            reservation.cancel()

        flight_reservations = FlightReservation.objects.filter(status=FlightReservation.STATUS_PENDING, created__lte=timeout)
        for flight_reservation in flight_reservations:
            flight_reservation.cancel()
