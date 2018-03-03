from django.core.management.base import BaseCommand
import arrow
from datetime import date, timedelta
from flights.models import AlertFlightNotification


class Command(BaseCommand):
    def handle(self, *args, **options):
        now = arrow.now().datetime
        cleanup_date = now - timedelta(days=15)
        list = AlertFlightNotification.objects.filter(createdon__lte=cleanup_date).all()
        for alert_flight in list:
            alert_flight.delete()
