from django.core.management.base import BaseCommand
from django.conf import settings
from datetime import timedelta
import arrow
from flights.models import Flight,FlightReservation
from reservations.models import Passenger
import logging
from htmlmailer.mailer import send_html_email

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    def handle(self, *args, **options):
        now = arrow.now().datetime
        lastweek = now - timedelta(days=7)
        flights = Flight.objects.filter(status=Flight.STATUS_COMPLETE,departure__gte=lastweek)
        flightreservationlist = FlightReservation.objects.filter(status=FlightReservation.STATUS_COMPLETE,flight=flights)
        passenger_list = Passenger.objects.filter(flight_reservation_id__in = flightreservationlist).values('email').distinct().all()
        context = {
        }
        subject = "Your Recent Rise Flight Experience"
        for email_obj in passenger_list:
            context['email'] = email_obj.get('email')
            send_html_email('emails/flight_feedback_email', context, subject, settings.DEFAULT_FROM_EMAIL, [email_obj.get('email')])

