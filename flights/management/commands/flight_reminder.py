from django.core.management.base import BaseCommand
from django.conf import settings
from datetime import date, timedelta
import arrow
import calendar
from flights.models import Flight,AlertFlightNotification,Airport
from announcements.models import AutomatedMessage
from accounts.models import OncallSchedule
import urllib2
import json
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    def handle(self, *args, **options):
        now = arrow.now().datetime
        tomorrow = now + timedelta(hours=24)
        flights = Flight.objects.filter(departure__gte=now,departure__lte=tomorrow,status__in=[Flight.STATUS_ON_TIME,Flight.STATUS_DELAYED]).all()
        for flight in flights:
            airport = Airport.objects.filter(id=flight.origin_id).first()
            if airport.map_url is None or len(airport.map_url) <= 0:
                address = airport.street_1 + ","+ airport.city + "," + airport.state + "," + airport.postal_code
                map_url = settings.GOOGLE_MAP_URL + address
                try:
                    request = urllib2.Request(settings.GOOGLE_URL_SHORTNER)
                    request.add_header('Content-Type', 'application/json')
                    postdata = {'longUrl':map_url}
                    response = urllib2.urlopen(request,json.dumps(postdata))
                    data = json.loads(response.read())
                    airport.map_url = data["id"]
                    airport.save()
                except Exception as e:
                    logger.exception(e)

            local_month_time = flight.local_departure_time_display_month_time()
            local_date = flight.local_departure_time_display_month()
            local_time = flight.local_departure_time_display()
            local_time_20_mins = flight.local_departure_time_20_mins_before()
            route = flight.origin.code + "-" + flight.destination.code
            time_diff = flight.departure-now
            hours = int(time_diff.total_seconds()/3600)
            oncall = OncallSchedule.objects.filter(flights=flight,airport_id=flight.origin_id).first()
            oncallname = 'your RISE Rep'
            if oncall is not None:
               oncallname = oncall.user.get_full_name()
            else:
                oncall = OncallSchedule.objects.filter(airport_id=flight.origin_id,start_date__lte=flight.departure,end_date__gte=flight.departure).first()
                if oncall is not None:
                    oncallname = oncall.user.get_full_name()
            flight_notification = AlertFlightNotification.objects.filter(flight_id = flight.id).first()
            if flight_notification is None:
                flight_notification = AlertFlightNotification()
                flight_notification.flight = flight
                flight_notification.createdon = now
                flight_notification.save()
            if hours <= 1:
                if not flight_notification.hour_1:
                    automated_message = AutomatedMessage.objects.filter(message_key=AutomatedMessage.FLIGHT_DEPARTURE_NOTIFICATION_1).first()
                    msg_txt = automated_message.sms_text
                    msg_txt = msg_txt.replace("[[flight]]",flight.flight_number)
                    msg_txt = msg_txt.replace("[[time]]",local_month_time)
                    msg_txt = msg_txt.replace("[[oncallname]]",oncallname)
                    flight_notification.send(msg_txt,sms_only=True)
                    msg_txt = automated_message.email_text
                    msg_txt = msg_txt.replace("[[origin-dest]]",route)
                    msg_txt = msg_txt.replace("[[flighttime]]",local_time)
                    msg_txt = msg_txt.replace("[[airportarrivaltime]]",local_time_20_mins)
                    msg_txt = msg_txt.replace("[[origin-directions-link]]",airport.map_url)
                    msg_txt = msg_txt.replace("[[oncallname]]",oncallname)
                    flight_notification.send(msg_txt,settings.FLIGHT_ALERT_SUBJECT_1_HOUR)
                    flight_notification.hour_1 = True
                    flight_notification.save()
            if hours <= 24:
                if not flight_notification.hour_24:
                    automated_message = AutomatedMessage.objects.filter(message_key=AutomatedMessage.FLIGHT_DEPARTURE_NOTIFICATION_24).first()
                    msg_txt = automated_message.sms_text
                    msg_txt = msg_txt.replace("[[flight]]",flight.flight_number)
                    msg_txt = msg_txt.replace("[[time]]",local_month_time)
                    msg_txt = msg_txt.replace("[[oncallname]]",oncallname)
                    flight_notification.send(msg_txt,sms_only=True)
                    msg_txt = automated_message.email_text
                    msg_txt = msg_txt.replace("[[flighttime]]",local_time)
                    msg_txt = msg_txt.replace("[[flightdate]]",local_date)
                    msg_txt = msg_txt.replace("[[origin-dest]]",route)
                    if airport.map_url is not None:
                        msg_txt = msg_txt.replace("[[origin-directions-link]]",airport.map_url)
                    flight_notification.send(msg_txt,settings.FLIGHT_ALERT_SUBJECT_24_HOURS)
                    flight_notification.hour_24 = True
                    flight_notification.save()
