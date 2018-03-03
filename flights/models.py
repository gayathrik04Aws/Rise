from django.conf import settings
from django.db import models, transaction
from django.db.models import Count, F, Q, Sum
from django.contrib.auth.models import Permission
from localflavor.us.models import USStateField
from pytz import common_timezones
import datetime
from datetime import timedelta, time
from auditlog.registry import auditlog
import arrow
import redis
from twilio.rest import TwilioRestClient

from htmlmailer.mailer import send_html_email
from icalendar import Calendar, Event
from django.core.mail import EmailMultiAlternatives
from core.tasks import send_html_email_task
from reservations.models import FlightReservation, Reservation, Passenger, FlightWaitlist
from accounts.models import Account, User
from billing.models import Plan
from rise import util
from .managers import FlightSearchManager
from . import const
import logging

logger = logging.getLogger(__name__)

TIMEZONE_CHOICES = [(tz, tz) for tz in common_timezones]


class Airport(models.Model):
    """
    Details about an airport where our flights will originate or their destinations

    name: The name of the airport
    code: The code of the airport
    street_1: Street address of the airport location users will go to
    street_2: Street address of the airport location users will go to
    city: City the airport is in
    postal_code: The postal code of the airport location
    state: The state of the airport location
    details: Text field for including extra details about an airport, perhaps more specific direction on where to go
    timezone: The name of the timezone the airport is located in for translating times
    """


    name = models.CharField(max_length=128)
    code = models.CharField(max_length=4, db_index=True)
    street_1 = models.CharField(max_length=128)
    street_2 = models.CharField(max_length=128, blank=True, null=True)
    city = models.CharField(max_length=64)
    postal_code = models.CharField(max_length=10)
    state = USStateField()
    details = models.TextField()
    timezone = models.CharField(max_length=32, choices=TIMEZONE_CHOICES, default='US/Central')
    map_url = models.CharField(max_length=150, blank=True, null=True)

    class Meta:
        ordering = ["name"]

    def __unicode__(self):
        return self.name


class Plane(models.Model):
    """
    Details about a plane
    """

    MODEL_CHOICES = (
        ('Beechcraft King Air 350', 'Beechcraft King Air 350'),
        ('Beechcraft King Air B200', 'Beechcraft King Air B200'),
    )

    model = models.CharField(max_length=64, choices=MODEL_CHOICES, default='Beechcraft King Air 350')
    registration = models.CharField(max_length=16)
    seats = models.PositiveIntegerField(default=8)
    reset_time = models.TimeField(default=time(0))

    def __init__(self, *args, **kwargs):
        """
        Save initial value for seats to check for change
        """
        super(Plane, self).__init__(*args, **kwargs)
        self.__seats = self.seats

    def save(self, *args, **kwargs):
        super(Plane, self).save(*args, **kwargs)

        # if the number of seats changed on a Plane
        if self.__seats != self.seats:
            # get a list of flights that are on time or delayed (no need to update older flights)
            flights = self.flight_set.filter(status__in=(Flight.STATUS_ON_TIME, Flight.STATUS_DELAYED)).select_related('plane')
            for flight in flights:
                flight.update_plane_seats_available()
                flight.save(update_fields=['seats_available', 'seats_total'])
                flight.refresh_from_db()
                flight.refresh_cache()

    def __unicode__(self):
        return '%s' % (self.registration,)


class BaseRoute(models.Model):
    """
    Abstract base class representing a route between two airports with duration

    name: A name for this route
    origin: The origin airport where the flight would originate
    destination: The destination airport where the flight would arrive
    duration: The duration of the flight in minutes
    """

    name = models.CharField(max_length=128)
    origin = models.ForeignKey('flights.Airport', related_name='origin_%(class)ss')
    destination = models.ForeignKey('flights.Airport', related_name='destination_%(class)ss')
    duration = models.PositiveIntegerField()

    class Meta:
        abstract = True

    def __unicode__(self):
        return 'Route %s -> %s in %s' % (self.origin.code, self.destination.code, self.duration)

    def duration_as_timedelta(self):
        """
        Returns Route.duration as a datetime.timedelta object with minutes set
        """
        return timedelta(minutes=self.duration)

    def duration_as_time(self):
        """
        Returns Route.duration as a datetime.time object
        """
        duration_minutes = self.duration
        minutes_in_hour = 60

        duration_hours = duration_minutes / minutes_in_hour
        duration_minutes = duration_minutes % minutes_in_hour
        return time(hour=duration_hours, minute=duration_minutes, second=0)


class Route(BaseRoute):
    """
    A basic/legacy Route.
    """
    plane = models.ForeignKey('flights.Plane', on_delete=models.SET_NULL, null=True)
    pass


class RouteTime(models.Model):
    """
    A template time/days for a given route

    route: The route to be flown
    departure: The given departure time for this route
    max_seats_corporate: How many seats may be reserved for Corporate users
    max_seats_companion: How many seats may be reserved for Companion users
    monday-sunday: The days of the week this route will be flown at the given departure time

    account_restrictions: Restrict this route time to the given accounts, if none, available to all
    """

    route = models.ForeignKey('flights.Route')
    flight_number = models.CharField(max_length=16)
    departure = models.TimeField()
    max_seats_corporate = models.PositiveIntegerField(null=True, default=4, help_text="How many seats may be reserved for Corporate users")
    max_seats_companion = models.PositiveIntegerField(null=True, default=4, help_text="How many seats may be reserved for Companion users")
    monday = models.BooleanField(default=False, blank=True)
    tuesday = models.BooleanField(default=False, blank=True)
    wednesday = models.BooleanField(default=False, blank=True)
    thursday = models.BooleanField(default=False, blank=True)
    friday = models.BooleanField(default=False, blank=True)
    saturday = models.BooleanField(default=False, blank=True)
    sunday = models.BooleanField(default=False, blank=True)
    plane = models.ForeignKey('flights.Plane', on_delete=models.SET_NULL, null=True)

    account_restriction = models.ManyToManyField('accounts.Account', blank=True)

    class Meta:
        ordering = ('departure',)

    def __unicode__(self):
        route = 'Route %s -> %s @ %s for %s on ' % (self.route.origin.code, self.route.destination.code, self.departure, self.route.duration)
        if self.monday:
            route += 'M'
        if self.tuesday:
            route += 'T'
        if self.wednesday:
            route += 'W'
        if self.thursday:
            route += 'R'
        if self.friday:
            route += 'F'
        if self.saturday:
            route += 'S'
        if self.monday:
            route += 'U'
        return route

    def set_plan_restrictions(self, restrictions):
        """
        Takes an iterable to two-tuples of (name, int) and an optional iterable of corporate accounts

        restrictions: iterable of two-tuples (name, days) where `name` is the name of a :class:`billing.models.Plan` and
            `days` is the int number of days the billing plan can reserve in advance
        """

        current_plan_restrictions = []
        for name, days in restrictions:
            p = Plan.objects.get(name__iexact=name)
            plan_restriction, created = RouteTimePlanRestriction.objects.get_or_create(plan=p, route_time=self)
            plan_restriction.days = days
            plan_restriction.save()
            current_plan_restrictions.append(plan_restriction.id)

        self.routetimeplanrestriction_set.exclude(id__in=current_plan_restrictions).delete()

    def set_plan_seat_restrictions(self, restrictions):
        """
        Takes an iterable to two-tuples of (name, int)

        restrictions: iterable of two-tuples (name, days) where `name` is the name of a :class:`billing.models.Plan` and
            `seats` is the int number of seats the billing plan can reserve
        """

        current_plan_seat_restrictions = []
        for name, seats in restrictions:
            p = Plan.objects.get(name__iexact=name)
            plan_restriction, created = RouteTimePlanSeatRestriction.objects.get_or_create(plan=p, route_time=self)
            plan_restriction.seats = seats
            plan_restriction.save()
            current_plan_seat_restrictions.append(plan_restriction.id)

        self.routetimeplanseatrestriction_set.exclude(id__in=current_plan_seat_restrictions).delete()


class RouteTimePlanRestriction(models.Model):
    """
    Allows a template route time to have flight plan restrictions.

    See FlightPlanRestriction model for implementation details.
    """

    route_time = models.ForeignKey('flights.RouteTime')
    plan = models.ForeignKey('billing.Plan')
    days = models.PositiveIntegerField(default=0)

    def __unicode__(self):
        return '%s - %s - %s' % (self.route_time.flight_number, self.plan.name, self.days)


class RouteTimePlanSeatRestriction(models.Model):
    """
    Allows a template route time to have flight plan seats restrictions.

    See FlightPlanSeatRestriction model for implementation details.
    """

    route_time = models.ForeignKey('flights.RouteTime')
    plan = models.ForeignKey('billing.Plan')
    seats = models.PositiveIntegerField(default=0)

    def __unicode__(self):
        return '%s - %s - %s' % (self.route_time.flight_number, self.plan.name, self.seats)


class AnywhereFlightDetails(models.Model):
    """
    Contains details only pertinent to a RISE Anywhere flight.
    """

    CONFIRMATION_STATUS_NOTREADY = 'NOTREADY'
    CONFIRMATION_STATUS_FULLPENDING = 'PENDINGCONFIRMATION'
    CONFIRMATION_STATUS_CONFIRMED = 'CONFIRMED'
    CONFIRMATION_STATUS_CANCELLED = 'CANCELLED'

    CONFIRMATION_STATUS_CHOICES = (
        (CONFIRMATION_STATUS_NOTREADY, 'Not Ready'),
        (CONFIRMATION_STATUS_FULLPENDING, 'Full - Pending Confirmation'),
        (CONFIRMATION_STATUS_CONFIRMED, 'Confirmed'),
        (CONFIRMATION_STATUS_CANCELLED, 'Cancelled'),
    )

    anywhere_request = models.ForeignKey('anywhere.AnywhereFlightRequest', null=True, on_delete=models.SET_NULL, blank=True)
    flight_creator_user = models.ForeignKey('accounts.User',null=True, on_delete=models.SET_NULL, blank=True)
    confirmation_status = models.CharField(max_length=20, choices=CONFIRMATION_STATUS_CHOICES, default=CONFIRMATION_STATUS_NOTREADY)
    full_flight_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    per_seat_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    sharing = models.CharField(max_length=12, choices=const.SHARING_CHOICES, default=const.SHARING_OPTION_PUBLIC)
    other_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    other_cost_desc = models.TextField(max_length=100, null=True, blank=True)


class Flight(models.Model):
    """
    An individual flight

    plane: The actual plane that will be flying this flight
    status: The status of this flight
    flight_type: The type of flight. Regularly scheduled  or a promotional flight or RiseAnywhere
    origin: Where this flight will takeoff from
    destination: Where this flight will land
    departure: Estimated departure time
    actual_departure: When this flight actually departed
    arrival: The estimated arrival time
    actual_arrival: When the flight actually arrived
    duration: The duration in minutes of the flight
    seats_total: The total number of seats on the plane that can be reserved
    seats_available: The total number of seats that are still available to be reserved
    seats_companion: The total number of seats on this flight that are reserved as companion seats
    max_seats_corporate: How many seats may be reserved for Corporate users
    max_seats_companion: How many seats may be reserved for Companion users
    route_time: Reference to the route time template that was used to create this flight if one was used
    surcharge: An additional cost for this flight
    account_restriction: Restrict this flight to the given accounts, if none, available to all
    vip: If true, restrict this flight to VIP accounts
    founder: If true, restrict this flight to Founder accounts
    pilot: the user who is the pilot, restricted to the Pilot user group
    copilot: the user who is the copilot, restricted to the Pilot user group
    anywhere_details:  Reference to the RiseAnywhere specific details of the flight.
    """

    STATUS_ON_TIME = 'O'
    STATUS_DELAYED = 'D'
    STATUS_CANCELLED = 'C'
    STATUS_IN_FLIGHT = 'F'
    STATUS_COMPLETE = 'L'  # L for landed

    STATUS_CHOICES = (
        (STATUS_ON_TIME, 'On-Time'),
        (STATUS_DELAYED, 'Delayed'),
        (STATUS_CANCELLED, 'Cancelled'),
        (STATUS_IN_FLIGHT, 'In-Flight'),
        (STATUS_COMPLETE, 'Complete'),
    )

    STATUS_CHANGE_GRAPH = {
        STATUS_ON_TIME: (STATUS_DELAYED, STATUS_CANCELLED, STATUS_IN_FLIGHT, STATUS_COMPLETE),
        STATUS_DELAYED: (STATUS_DELAYED, STATUS_ON_TIME, STATUS_CANCELLED, STATUS_IN_FLIGHT, STATUS_COMPLETE),
        STATUS_IN_FLIGHT: (STATUS_COMPLETE,),
        STATUS_CANCELLED: (),
        STATUS_COMPLETE: (),
    }

    TYPE_REGULAR = 'R'
    TYPE_PROMOTION = 'P'
    TYPE_FUN = 'F'
    TYPE_ANYWHERE = 'A'

    #Anywhere does not get added to this list because there is a separate flight creation workflow for Anywhere flights
    TYPE_CHOICES = (
        (TYPE_REGULAR, 'Regularly Scheduled Flight'),
        (TYPE_PROMOTION, 'Promotional Flight'),
        (TYPE_FUN, 'Fun Flight'),
    )

    flight_number = models.CharField(max_length=16)
    plane = models.ForeignKey('flights.Plane', on_delete=models.SET_NULL, null=True)
    status = models.CharField(max_length=1, choices=STATUS_CHOICES, default=STATUS_ON_TIME)
    flight_type = models.CharField(max_length=1, choices=TYPE_CHOICES, default=TYPE_REGULAR)
    origin = models.ForeignKey('flights.Airport', related_name='origin_flights')
    destination = models.ForeignKey('flights.Airport', related_name='destination_flights')
    departure = models.DateTimeField()
    actual_departure = models.DateTimeField(blank=True, null=True)
    arrival = models.DateTimeField()
    actual_arrival = models.DateTimeField(blank=True, null=True)
    duration = models.PositiveIntegerField()
    seats_total = models.PositiveIntegerField(default=8)
    seats_available = models.IntegerField(default=8)
    seats_companion = models.IntegerField(default=0)
    max_seats_corporate = models.PositiveIntegerField(null=True, help_text="How many seats may be reserved for Corporate users")
    max_seats_companion = models.PositiveIntegerField(null=True, help_text="How many seats may be reserved for Companion users")
    route_time = models.ForeignKey('flights.RouteTime', on_delete=models.SET_NULL, null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True)
    surcharge = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    account_restriction = models.ManyToManyField('accounts.Account', blank=True)
    vip = models.BooleanField(default=False, help_text="Restrict flight to VIP accounts")
    founder = models.BooleanField(default=False, help_text="Restrict flight to Founder accounts")
    pilot = models.ForeignKey('accounts.User', limit_choices_to={'groups__name': "Pilot"}, on_delete=models.SET_NULL, null=True, blank=True, related_name='piloted_flights')
    copilot = models.ForeignKey('accounts.User', limit_choices_to={'groups__name': "Pilot"}, on_delete=models.SET_NULL, null=True, blank=True, related_name='copiloted_flights')
    anywhere_details = models.ForeignKey('flights.AnywhereFlightDetails', on_delete=models.SET_NULL, null=True)
    objects = models.Manager()
    search = FlightSearchManager()

    def cache_key(self, name):
        """
        Returns a cache key for the given name.

        THE NAME SHOULD MATCH THE FIELD NAME OF THE VALUE BEING CACHED.
        """
        return 'flight-%d-%s' % (self.pk, name)

    def refresh_cache(self):
        """
        refreshes the cache for a list of fields
        """
        r = redis.from_url(settings.REDIS_URL)

        fields = ['seats_available']

        for field in fields:
            cache_key = self.cache_key(field)
            value = getattr(self, field)
            r.set(cache_key, value)

    def ical(self):
        """
        Creates and returns the iCal file for this flight
        """
        cal = Calendar()
        cal.add('version', '2.0')
        cal.add('method', 'REQUEST')
        cal.add('CALSCALE', 'GREGORIAN')

        cal.add_component(self.ical_event())

        return cal

    def ical_event(self, attendees=None):
        """
        Creates and returns the iCal event for this flight
        """
        event = Event()
        event.add('summary', 'Rise Flight %s' % (self.flight_number,))
        event.add('dtstart', self.departure)
        event.add('dtend', self.arrival)
        event.add('uid', self.pk)
        event.add('SEQUENCE', '0')
        event.add('STATUS', 'CONFIRMED')
        event.add('organizer;CN="Rise":mailto', 'ops@iflyrise.com')
        event.add('TRANSP','OPAQUE')

        if attendees != None:
            for attendee in attendees:
                event.add('ATTENDEE;CUTYPE=INDIVIDUAL;ROLE=REQ-PARTICIPANT;PARTSTAT=ACCEPTED;RSVP=TRUE;CN=' + str(attendee) + ';X-NUM-GUESTS=0:mailto', attendee)

        return event

    def in_flight(self):
        """
        Marks a flight as in-flight

        Update actual departure time
        """
        departure = arrow.now(self.origin.timezone).datetime
        Flight.objects.filter(id=self.id).update(actual_departure=departure)

    def complete(self, flightset=None, completed_by=None):
        """
        Mark a flight as completed

        - updates actual arrival time
        - Free account resources for those on this flight
        """
        arrival = arrow.now(self.destination.timezone).datetime
        Flight.objects.filter(id=self.id).update(actual_arrival=arrival)


        # free account resources
        for flight_reservation in self.flightreservation_set.exclude(status__in=(FlightReservation.STATUS_CANCELLED, FlightReservation.STATUS_PENDING, FlightReservation.STATUS_COMPLETE, FlightReservation.STATUS_PARTIALNOSHOW, FlightReservation.STATUS_NOSHOW)):
            #  handle no-shows.
            noshowcount = 0
            passengers = Passenger.objects.filter(flight_reservation_id=flight_reservation.id).all()
            for passenger in passengers:
                if not passenger.checked_in:
                    noshowcount+=1
                    passenger.handle_noshow(completed_by)
            # depending on how many no shows we have, is what the final reservation status will be.

            if noshowcount == passengers.count():
                flight_reservation.noshow()
            elif noshowcount > 0:
                flight_reservation.partialnoshow()
            else:
                flight_reservation.complete()

            flight_reservation.free_account_passes()

        # clear any lingering waitlist entries which still have a status of waiting, make them expired
        # so we can tell difference between expired & user cancelled.
        for waiting in self.flightwaitlist_set.filter(status=FlightWaitlist.STATUS_WAITING):
            waiting.expire()

        if self.flight_type == Flight.TYPE_ANYWHERE and flightset:
            # process any outstanding refunds
            flightset.update_final_costs()
            flightset.process_overpaid_passenger_refunds(completed_by)

        context = {
            'flight': self,
        }
        subject = "Your Recent Rise Flight Experience"

        passengers = self.get_passengers()
        for passenger in passengers:
            context['email'] = passenger.email
            send_html_email('emails/flight_feedback_email', context, subject, settings.DEFAULT_FROM_EMAIL, [passenger.email])


    def local_departure(self):
        """
        Return the depature time localized to the origin timezone
        """
        return arrow.get(self.departure).to(self.origin.timezone).datetime

    def local_departure_year_digit(self):
        time = self.local_departure()
        return time.strftime("%Y")

    def local_departure_month_digit(self):
        time = self.local_departure()
        return time.strftime("%-m")

    def local_departure_day_digit(self):
        time = self.local_departure()
        return time.strftime("%-d")

    def local_departure_dateonly(self):
        time = self.local_departure()
        return time.strftime("%x")

    def local_departure_display(self):
        time = self.local_departure()
        return time.strftime("%b %d, %Y %-I:%M%p")

    def local_departure_time_display(self):
        time = self.local_departure()
        return time.strftime("%-I:%M%p")

    def local_departure_time_20_mins_before(self):
        time = self.local_departure() - datetime.timedelta(minutes=20)
        return time.strftime("%-I:%M%p")

    def local_departure_time_display_month_time(self):
        time = self.local_departure()
        return time.strftime("%b %d %-I:%M%p")

    def local_departure_time_display_month(self):
        time = self.local_departure()
        return time.strftime("%b %d")

    def local_actual_departure(self):
        """
        Return the actual depature time localized to the origin timezone
        """
        return arrow.get(self.actual_departure).to(self.origin.timezone).datetime

    def local_arrival(self):
        """
        Return the arrival time localized to the destination timezone
        """
        return arrow.get(self.arrival).to(self.destination.timezone).datetime

    def local_arrival_time_display(self):
        time = self.local_arrival()
        return time.strftime("%-I:%M%p")

    def local_actual_arrival(self):
        """
        Return the actual arrival time localized to the destination timezone
        """
        return arrow.get(self.actual_arrival).to(self.destination.timezone).datetime

    def can_change_status(self):
        """
        Determines based on current status if any status changes can occur
        """
        statuses = Flight.STATUS_CHANGE_GRAPH.get(self.status)
        return len(statuses) > 0

    def status_choices(self):
        """
        Returns status choices for a form for the current status
        """
        statuses = Flight.STATUS_CHANGE_GRAPH.get(self.status)

        choice_dict = dict(Flight.STATUS_CHOICES)

        choices = [(status, choice_dict.get(status)) for status in statuses]
        return choices

    def cancel(self, refund_eligible=False):
        """
        Cancel a flight.

        Cancel any flight reservations to free account resources

        Some flights are refund eligible and some are not.  Anywhere flights that are a return leg w/ less than 2 days between
        legs can't be refunded because the leg itself is the rehoming charge.

        """
        self.status = Flight.STATUS_CANCELLED
        self.save()

        if self.flight_type == Flight.TYPE_ANYWHERE:
            self.anywhere_details.confirmation_status = AnywhereFlightDetails.CONFIRMATION_STATUS_CANCELLED
            self.anywhere_details.save()

        flight_reservations = FlightReservation.objects.filter(flight=self)

        messages = ""
        for flight_reservation in flight_reservations:
            from billing.models import GenericBillingException
            try:
                # free account passes including complimentary ones since it was cancelled
                flight_reservation.free_account_passes(complimentary=True)
                flight_reservation.cancel(flight_cancelled=True, refund_eligible=refund_eligible)
            except GenericBillingException as gbe:
                messages += "Flight Reservation %s refund failed." % (flight_reservation.id)

            # if any reservations have no non-cancelled flights, cancel them
            reservation = flight_reservation.reservation
            livecount = reservation.flightreservation_set.exclude(status=FlightReservation.STATUS_CANCELLED).count()
            if livecount == 0:
                reservation.cancel(try_void_charge=refund_eligible)
                reservation.save()
        return messages

    def refund_previously_cancelled_reservations(self):
        flight_reservations = FlightReservation.objects.filter(flight=self)
        msgs = ""
        from billing.models import GenericBillingException
        for fr in flight_reservations:
            try:
                fr.refund_only()
            except GenericBillingException as gbe:
                msgs += "Flight reservation % failed to refund. " % fr.id

        return msgs

    def delay(self, new_departure):
        """
        Delays a flight with the given new departure date/time
        """
        self.status = Flight.STATUS_DELAYED

        self.departure = new_departure
        self.arrival = self.departure + timedelta(minutes=self.duration)

        self.save()

    def send_marketing_flight_email(self):
        """
        Send marketing flight email, either promo or fun
        """
        if not self.is_fun_flight() and not self.is_promotional_flight():
            return None

        users = self.eligible_marketing_users()

        if self.is_fun_flight():
            subject = 'Upcoming Rise Fun Flight'
            template = 'emails/fun_flight'
        else:
            subject = 'Upcoming Rise Promo Flight'
            template = 'emails/promo_flight'

        context = {
            'flight': self,
        }

        for user in users:
            send_html_email(template, context, subject, settings.DEFAULT_FROM_EMAIL, [user.email])

    def eligible_marketing_users(self):
        """
        Returns a list of eligible users for this flight
        """
        # first get all users that can fly
        perm = Permission.objects.get(codename='can_fly')
        flying_users = set(list(User.objects.filter(Q(groups__permissions=perm) | Q(user_permissions=perm)).distinct().values_list('id', flat=True)))

        # get users that can book promo flights
        perm = Permission.objects.get(codename='can_book_promo_flights')
        promo_users = set(list(User.objects.filter(Q(groups__permissions=perm) | Q(user_permissions=perm)).distinct().values_list('id', flat=True)))

        eligible_users = flying_users & promo_users

        return User.objects.filter(id__in=eligible_users, user_profile__alert_promo_email=True, is_active=True, account__status=Account.STATUS_ACTIVE)

    def is_fun_flight(self):
        """
        Returns True if this flight is a fun flight
        """
        return self.flight_type == Flight.TYPE_FUN

    def is_promotional_flight(self):
        """
        Return True if this is a promotional flight
        """
        return self.flight_type == Flight.TYPE_PROMOTION

    def is_regular_flight(self):
        """
        Return True if this is just a regular flight
        """
        return self.flight_type == Flight.TYPE_REGULAR

    def is_anywhere_flight(self):
        """

        Returns: True if this is a RiseAnywhere flight

        """
        return self.flight_type == Flight.TYPE_ANYWHERE

    def is_cancelled(self):
        """
        Returns true if this flight is cancelled
        """
        return self.status == Flight.STATUS_CANCELLED

    def is_delayed(self):
        """
        Returns true if this flight is delayed
        """
        return self.status == Flight.STATUS_DELAYED

    def is_inflight(self):
        """
        Returns true if this flight is delayed
        """
        return self.status == Flight.STATUS_IN_FLIGHT

    def is_complete(self):
        """
        Returns true if this flight is complete
        """
        return self.status == Flight.STATUS_COMPLETE

    def duration_as_timedelta(self):
        """
        Returns flight.duration as a datetime.timedelta object with minutes set
        """
        return timedelta(minutes=self.duration)

    def duration_as_time(self):
        """
        Returns flight.duration as a datetime.time object
        """
        try:
            return util.duration_as_time(self.duration)
        except:  # except what?
            return None

    def __str__(self):
        return self.flight_number + ": " + self.origin.city + "-" + self.destination.city + " at " + self.local_departure_display()

    def is_booked_by_user(self, userprofile):
        """
        Returns True if this flight is already booked by this userprofile.
        """
        return Passenger.objects.filter(flight_reservation__flight__id=self.id, userprofile__id=userprofile.id, flight_reservation__status__in=(FlightReservation.STATUS_RESERVED, FlightReservation.STATUS_CHECKED_IN, FlightReservation.STATUS_PENDING, FlightReservation.STATUS_ANYWHERE_PENDING)).exists()

    def reserve_anywhere_flight(self, created_by, userprofile, seats, cost, reservation=None):
        """
        Anywhere flights have a separate reservation process
         -- they all have a charge associated, but the charge is NOT made at reservation time, it's made when the flight confirms
         -- they do NOT decrement any passes
         -- all legs in an AnywhereFlightSet must be booked together.



        Args:
            created_by: the User creating the reservation
            user: the User this reservation is for
            reservation: if this goes onto an existing Reservation this will be populated otherwise create new.

        Returns: a flight reservation

        """
        if self.is_booked_by_user(userprofile):
            return None

        # if there is not already a reservation session started, create one
        if reservation is not None:
            # see if there are already pending flight reservation for this flight/reservation
            flight_reservations = FlightReservation.objects.filter(reservation=reservation, flight=self, status=FlightReservation.STATUS_PENDING)
            # cancel any existing ones and start new
            for flight_reservation in flight_reservations:
                flight_reservation.cancel()

        with transaction.atomic():
            # get redis
            r = redis.from_url(settings.REDIS_URL)
            # get the redis key for seats available and the number of passengers
            seats_available_key = self.cache_key('seats_available')
            passenger_count = seats
            #if seats to book is -1, this means book all seats on the plane
            if seats == -1:
                seats = self.plane.seats
                passenger_count = self.plane.seats

            # use Redis as a method of atomicaly acquiring seats on a flight
            with r.pipeline() as pipe:
                while 1:
                    try:
                        # put a WATCH on the key that holds our sequence value
                        pipe.watch(seats_available_key)
                        # after WATCHing, the pipeline is put into immediate execution
                        # mode until we tell it to start buffering commands again.
                        # this allows us to get the current value of our sequence
                        current_value = pipe.get(seats_available_key) or self.seats_total
                        next_value = int(current_value) - passenger_count
                        if next_value < 0:
                            return None
                        # now we can put the pipeline back into buffered mode with MULTI
                        pipe.multi()
                        pipe.set(seats_available_key, next_value)
                        # and finally, execute the pipeline (the set command)
                        pipe.execute()
                        # if a WatchError wasn't raised during execution, everything we just did happened atomically.

                        # update database with seat counts
                        Flight.objects.filter(id=self.id).update(seats_available=F('seats_available') - seats)

                        #if all the seats are booked we need to flag the status on the anywhere details
                        if next_value == 0:
                            self.anywhere_details.confirmation_status = self.anywhere_details.CONFIRMATION_STATUS_FULLPENDING
                        break
                    except redis.WatchError:
                        # another client must have changed our key between
                        # the time we started WATCHing it and the pipeline's execution.
                        # our best bet is to just retry.
                        continue

            if reservation is None:
                #note - can't test with superusers that have no accounts.
                reservation = Reservation.objects.create(account=userprofile.account, created_by=created_by, status=Reservation.STATUS_ANYWHERE_PENDING)

            tax = cost * settings.FET_TAX
            # create the flight reservation
            flight_reservation = FlightReservation.objects.create(
                reservation=reservation,
                flight=self,
                created_by=created_by,
                passenger_count=passenger_count,
                pass_count=0,
                complimentary_pass_count=0,
                companion_pass_count=0,
                complimentary_companion_pass_count=0,
                buy_pass_count=0,
                buy_companion_pass_count=0,
                cost=cost,
                tax=tax,
                status=FlightReservation.STATUS_ANYWHERE_PENDING
            )

            # at least add the flying user as a passenger
            flight_reservation.add_passenger(userprofile)
        return flight_reservation

    def reserve_flight(self, created_by, userprofile, reservation, companion_count=0, user_is_not_passenger=False, addl_member_count=0):
        """
        Reserve a flight for a given user

        created_by: The user creating this resveration
        user: the user this reservation is for
        reservation: If there is an existing pending reservation, otherwise if None, create one to use
        user_is_not_passenger:  Set to true if a member is booking a companion w/o joining the flight themselves
        --Does not apply for anywhere flights which don't have a concept of companions.

        Returns a flight reservation
        """

        #if this is an Anywhere flight we need to go through the anywhere reservation process instead of this one.
        if self.flight_type == 'A':
            return self.reserve_anywhere_flight(created_by, userprofile, 1+companion_count, reservation)

        # run through some quick checks to make sure this user can reserve this flight again
        if not self.check_account_restriction(userprofile):
            return None

        if not self.check_vip(userprofile):
            return None

        if not self.check_founder(userprofile):
            return None

        if not self.check_user_permissions(userprofile, companion_count):
            return None

        if not self.check_plan_restrictions(userprofile, companion_count):
            return None

        if not self.check_plan_seat_restrictions(userprofile, (1 + companion_count)):
            return None

        if self.is_booked_by_user(userprofile) and not user_is_not_passenger:
            # if they are already booked on the flight and this booking is for companions only we can let it through.
            return None

        # if there is already a reservation session started
        if reservation is not None:
            # see if there are already pending flight reservation for this flight/reservation
            flight_reservations = FlightReservation.objects.filter(reservation=reservation, flight=self, status=FlightReservation.STATUS_PENDING)
            # cancel any existing ones and start new
            for flight_reservation in flight_reservations:
                flight_reservation.cancel()

        # perform all of these database actions within a transaction
        with transaction.atomic():
            # get redis
            r = redis.from_url(settings.REDIS_URL)
            # get the redis key for seats available and the number of passengers
            seats_available_key = self.cache_key('seats_available')
            if not user_is_not_passenger:
                passenger_count = 1 + companion_count + addl_member_count
            else:
                passenger_count = companion_count + addl_member_count

            # use Redis as a method of atomicaly acquiring seats on a flight
            with r.pipeline() as pipe:
                while 1:
                    try:
                        # put a WATCH on the key that holds our sequence value
                        pipe.watch(seats_available_key)
                        # after WATCHing, the pipeline is put into immediate execution
                        # mode until we tell it to start buffering commands again.
                        # this allows us to get the current value of our sequence
                        current_value = pipe.get(seats_available_key) or self.seats_total
                        next_value = int(current_value) - passenger_count
                        if next_value < 0:
                            return None
                        # now we can put the pipeline back into buffered mode with MULTI
                        pipe.multi()
                        pipe.set(seats_available_key, next_value)
                        # and finally, execute the pipeline (the set command)
                        pipe.execute()
                        # if a WatchError wasn't raised during execution, everything we just did happened atomically.

                        # update database with seat counts
                        Flight.objects.filter(id=self.id).update(seats_available=F('seats_available') - passenger_count, seats_companion=F('seats_companion') + companion_count)

                        break
                    except redis.WatchError:
                        # another client must have changed our key between
                        # the time we started WATCHing it and the pipeline's execution.
                        # our best bet is to just retry.
                        continue

            # get redis keys for available and complimentary passes
            available_passes_key = userprofile.account.get_cache_key('available_passes')
            complimentary_passes_key = userprofile.account.get_cache_key('complimentary_passes')

            # the number of save my seat passes needed
            # regular members use passes
            if not user_is_not_passenger:
                passes_needed = 1 + addl_member_count
            else:
                passes_needed = 0 + addl_member_count

            # number of available passes used on an account
            available_passes_used = 0
            # number of complimentary passes used
            complimentary_passes_used = 0
            # number of passes that will need to be bought
            buy_pass_count = 0

            complimentary_companion_passes_used = 0
            companion_passes_used = 0
            buy_companion_pass_count = 0

            if self.flight_type != 'F':

                with r.pipeline() as pipe:
                    while 1:
                        try:
                            # reset counts in case we looped
                            available_passes_used = 0
                            complimentary_passes_used = 0
                            buy_pass_count = 0

                            pipe.watch(available_passes_key)
                            pipe.watch(complimentary_passes_key)

                            # get the number of complimentary and available passse for the account
                            complimentary_passes = int(pipe.get(complimentary_passes_key) or userprofile.account.complimentary_passes)
                            available_passes = int(pipe.get(available_passes_key) or userprofile.account.available_passes)


                            # track how many passes are still needed
                            # use expiring ones first, not complimentary
                            remaining_passes_needed = passes_needed
                            if available_passes > 0:
                                # if there are enough avilable passes
                                if available_passes >= remaining_passes_needed:
                                    # subtract used passes
                                    available_passes -= remaining_passes_needed
                                    # account for passes used
                                    available_passes_used += remaining_passes_needed
                                    # no more needed
                                    remaining_passes_needed = 0
                                else:
                                    # set number used to the number left
                                    available_passes_used = available_passes
                                    # see how many remaining we need
                                    remaining_passes_needed -= available_passes
                                    # set availible passes to 0
                                    available_passes = 0


                            # if there are complimentary passes available to use, acquire them next
                            if remaining_passes_needed > 0 and complimentary_passes > 0:
                                # if there are enough complimentary passes available to cover the number of passes needed
                                if complimentary_passes >= remaining_passes_needed:
                                    # subtract the passes needed from the complimentary total
                                    complimentary_passes -= remaining_passes_needed
                                    # record the number of complimentary passes used
                                    complimentary_passes_used = remaining_passes_needed
                                    # no more passes needed
                                    remaining_passes_needed = 0
                                else:
                                    # set the number of used complimentary passes to the number of complimentary passes available
                                    complimentary_passes_used = complimentary_passes
                                    # subtract from remaining passes needed
                                    remaining_passes_needed -= complimentary_passes
                                    # set available complimentary pass count to 0
                                    complimentary_passes = 0

                            # if there are still passes needed and there are passes available on the account

                            # # track how many passes are still needed
                            # remaining_passes_needed = passes_needed
                            # # if there are complimentary passes available to use, acquire them first
                            # if complimentary_passes > 0:
                            #     # if there are enough complimentary passes available to cover the number of passes needed
                            #     if complimentary_passes >= remaining_passes_needed:
                            #         # subtract the passes needed from the complimentary total
                            #         complimentary_passes -= remaining_passes_needed
                            #         # record the number of complimentary passes used
                            #         complimentary_passes_used = remaining_passes_needed
                            #         # no more passes needed
                            #         remaining_passes_needed = 0
                            #     else:
                            #         # set the number of used complimentary passes to the number of complimentary passes available
                            #         complimentary_passes_used = complimentary_passes
                            #         # subtract from remaining passes needed
                            #         remaining_passes_needed -= complimentary_passes
                            #         # set available complimentary pass count to 0
                            #         complimentary_passes = 0
                            #
                            # # if there are still passes needed and there are passes available on the account
                            # if remaining_passes_needed > 0 and available_passes > 0:
                            #     # if there are enough avilable passes
                            #     if available_passes >= remaining_passes_needed:
                            #         # subtract used passes
                            #         available_passes -= remaining_passes_needed
                            #         # account for passes used
                            #         available_passes_used += remaining_passes_needed
                            #         # no more needed
                            #         remaining_passes_needed = 0
                            #     else:
                            #         # set number used to the number left
                            #         available_passes_used = available_passes
                            #         # see how many remaining we need
                            #         remaining_passes_needed -= available_passes
                            #         # set availible passes to 0
                            #         available_passes = 0

                            # if there are still passes needed, and complimentary and available passes have been exhausted, buy them
                            if remaining_passes_needed > 0:
                                buy_pass_count += remaining_passes_needed

                            pipe.multi()
                            pipe.set(available_passes_key, available_passes)
                            pipe.set(complimentary_passes_key, complimentary_passes)
                            pipe.execute()

                            # update the account database with number of complimentary passes and available passes used
                            Account.objects.filter(id=userprofile.account.id).update(complimentary_passes=F('complimentary_passes') - complimentary_passes_used, available_passes=F('available_passes') - available_passes_used)

                            break
                        except redis.WatchError:
                            continue

                    available_companion_passes_key = userprofile.account.get_cache_key('available_companion_passes')
                    complimentary_companion_passes_key = userprofile.account.get_cache_key('complimentary_companion_passes')

                    complimentary_companion_passes_used = 0
                    companion_passes_used = 0
                    buy_companion_pass_count = 0

                    with r.pipeline() as pipe:
                        while 1:
                            try:
                                # reset counters if looped
                                complimentary_companion_passes_used = 0
                                companion_passes_used = 0
                                buy_companion_pass_count = 0

                                pipe.watch(available_companion_passes_key)
                                pipe.watch(complimentary_companion_passes_key)

                                # get avilable pass counts from account
                                complimentary_companion_passes = int(pipe.get(complimentary_companion_passes_key) or userprofile.account.complimentary_companion_passes)
                                available_companion_passes = int(pipe.get(available_companion_passes_key) or userprofile.account.available_companion_passes)

                                # get the number of passes needed
                                remaining_companion_passes = companion_count

                                   # if monthly passes are available use them first
                                if available_companion_passes > 0:
                                    # if there are enough monthy passes available
                                    if available_companion_passes >= companion_count:
                                        companion_passes_used += companion_count
                                        available_companion_passes -= companion_count
                                        remaining_companion_passes -= companion_count
                                    else:
                                        companion_passes_used = available_companion_passes
                                        remaining_companion_passes = companion_count - companion_passes_used
                                        available_companion_passes = 0

                                if remaining_companion_passes > 0 and complimentary_companion_passes > 0:
                                    if complimentary_companion_passes >= remaining_companion_passes:
                                        complimentary_companion_passes_used += remaining_companion_passes
                                        complimentary_companion_passes -= companion_passes_used
                                        remaining_companion_passes = 0
                                    else:
                                        complimentary_companion_passes_used = complimentary_companion_passes
                                        remaining_companion_passes -= complimentary_companion_passes_used
                                        complimentary_companion_passes = 0

                                # # if complimentary passes are available
                                # if complimentary_companion_passes > 0:
                                #     # if there are enough complimentary passes available
                                #     if complimentary_companion_passes >= companion_count:
                                #         complimentary_companion_passes_used += companion_count
                                #         complimentary_companion_passes -= companion_count
                                #         remaining_companion_passes -= companion_count
                                #     else:
                                #         complimentary_companion_passes_used = complimentary_companion_passes
                                #         remaining_companion_passes = companion_count - complimentary_companion_passes_used
                                #         complimentary_companion_passes = 0
                                #
                                # if remaining_companion_passes > 0 and available_companion_passes > 0:
                                #     if available_companion_passes >= remaining_companion_passes:
                                #         companion_passes_used += remaining_companion_passes
                                #         available_companion_passes -= companion_passes_used
                                #         remaining_companion_passes = 0
                                #     else:
                                #         companion_passes_used = available_companion_passes
                                #         remaining_companion_passes -= companion_passes_used
                                #         available_companion_passes = 0

                                if remaining_companion_passes > 0:
                                    buy_companion_pass_count += remaining_companion_passes

                                pipe.multi()
                                pipe.set(available_companion_passes_key, available_companion_passes)
                                pipe.set(complimentary_companion_passes_key, complimentary_companion_passes)
                                pipe.execute()

                                # update the account database with number of complimentary passes and available passes used
                                Account.objects.filter(id=userprofile.account.id).update(complimentary_companion_passes=F('complimentary_companion_passes') - complimentary_companion_passes_used, available_companion_passes=F('available_companion_passes') - companion_passes_used)

                                break
                            except redis.WatchError:
                                continue
            #end condition if the flight is not fun flight


            # if there is no existing reservation, create one
            if reservation is None:
                reservation = Reservation.objects.create(account=userprofile.account, created_by=created_by)

            # create the flight reservation
            flight_reservation = FlightReservation.objects.create(
                reservation=reservation,
                flight=self,
                created_by=created_by,
                passenger_count=passenger_count,
                pass_count=available_passes_used,
                complimentary_pass_count=complimentary_passes_used,
                companion_pass_count=companion_passes_used,
                complimentary_companion_pass_count=complimentary_companion_passes_used,
                buy_pass_count=buy_pass_count,
                buy_companion_pass_count=buy_companion_pass_count,
            )

            # at least add the flying user as a passenger
            # AMF - if there is a member user only.  If they are all companions we add later.
            if not user_is_not_passenger:
                flight_reservation.add_passenger(userprofile)

            return flight_reservation

    def check_user_permissions(self, userprofile, companion_count=0):
        """
        Check's a user's permissions to make sure they can book this flight

        Returns True if the user can book this flight, False if not
        Has to assume companions who don't have user accounts can fly (but not promo), otherwise they wouldn't exist.
        """
        if not userprofile.user:
            #companions wouldn't have had accounts.can_book_promo_flights perm, only can_fly.
            if self.flight_type == Flight.TYPE_PROMOTION:
                return False
            return True

        # if this user doesn't have flying permissions
        can_fly = userprofile.user.has_perm('accounts.can_fly')
        if not can_fly:
            return False

        promo_eligible = userprofile.user.has_perm('accounts.can_book_promo_flights')

        if not promo_eligible and self.flight_type == Flight.TYPE_PROMOTION:
            return False

        return True

    def check_plan_restrictions(self, userprofile, companion_count=0):
        """
        Determine if the user can book this flight based on their plan.

        Returns True if the user can book this flight, False if not
        """
        # Corporate users get a pass here for now.
        if userprofile.account.is_corporate():
            return True

        # VIP users get a pass as well
        if userprofile.account.vip:
            return True

        # find any restrictions
        restriction = next(iter(FlightPlanRestriction.objects.filter(flight=self, plan__id=userprofile.account.plan_id)), None)

        # if no restrictions found, then good to go
        if restriction is None:
            return True

        delta = self.departure - arrow.now().datetime
        if delta.days >= restriction.days:
            return False

        return True

    def check_plan_seat_restrictions(self, userprofile, seats):
        """
        Determine if the user can book the number seats on this flight based on their plan.

        Returns True if the user can book the seats on this flight, False if not
        """
        # Corporate users get a pass here for now.
        if userprofile.account.is_corporate():
            return True

        # find any restrictions
        restriction = next(iter(FlightPlanSeatRestriction.objects.filter(flight=self, plan__id=userprofile.account.plan_id)), None)

        # if no restrictions found, then good to go
        if restriction is None:
            return True
        else:
            available_seats = restriction.seats - self.get_plan_seats(userprofile.account.plan)
            if seats > available_seats:
                return False

        return True

    def check_account_restriction(self, userprofile):
        """
        Determine if this account is eligible to book this flight.

        Returns True if the user can book this flight, False if not
        """
        # TODO: make this check a denormalized boolean on the flight model or redis cache list of account ids
        # if this flight has account restrictions
        if self.account_restriction.exists():
            # check if this user's account is in the allowed account list
            return self.account_restriction.filter(id=userprofile.account.id).exists()

        return True

    def check_vip(self, userprofile):
        """
        Determine if this flight is restricted to VIP accounts.

        Returns True if the user can book this flight, False if not
        """
        if self.vip:
            # check if this user's account is in the allowed account list
            return self.vip == userprofile.account.vip

        return True

    def check_founder(self, userprofile):
        """
        Determine if this flight is restricted to Founder accounts.

        Returns True if the user can book this flight, False if not
        """
        if self.founder:
            # check if this user's account is in the allowed account list
            return self.founder == userprofile.account.founder

        return True

    def no_seats(self):
        """
        Determine if this flight has absolutely no seats
        """
        if self.seats_available > 0:
            return False
        else:
            return True

    def percent_full(self):
        """
        Used for RiseAnywhere flights to display % full, when the flight can be confirmed
        Returns: percentage of seats that are booked

        """
        if self.no_seats():
            return 100
        if self.seats_total > 0:
            return ((self.seats_total - self.seats_available) / self.seats_total) * 100
        #seats_total should never be 0 but we can't calculate percentage if it is.
        return 0

    def get_plan_seats(self, plan):
        """
        Retrieves the number of seats on the flight from accounts connected to the given plan
        """
        passenger_count = FlightReservation.objects.filter(flight=self, reservation__account__plan=plan, status__in=(FlightReservation.STATUS_RESERVED, FlightReservation.STATUS_CHECKED_IN, FlightReservation.STATUS_COMPLETE)).aggregate(Sum('passenger_count')).get('passenger_count__sum')
        if passenger_count:
            return passenger_count
        else:
            return 0

    def is_flight_full(self, user, companion_count=0, user_is_not_flying=False):
        """
        Determine if this flight is full for the given user
        """
        # get the total number of passengers
        if not user_is_not_flying:
            passenger_count = 1 + companion_count
        else:
            passenger_count = companion_count

        # if the number of requested passengers exceeds the number of seats available, it is full
        if passenger_count > self.seats_available:
            return True

        # if the user is requesting companion seats, see if there are any available
        if companion_count > 0:
            # get the number of total companions that would be on the flight
            total_companions = self.seats_companion + companion_count

            # if that total exceeds the allowed amount, the flight is full
            if total_companions > self.max_seats_companion:
                return True

        # if this user is a corporate account user, check corporate seats taken
        if user.account.is_corporate():
            # get the number of passengers already booked under this corporation
            account_passenger_count = FlightReservation.objects.filter(flight=self, reservation__account=user.account, status__in=(FlightReservation.STATUS_RESERVED, FlightReservation.STATUS_CHECKED_IN, FlightReservation.STATUS_COMPLETE)).aggregate(Count('passenger_count')).get('passenger_count__count')

            # get the total number of corporate passengers
            total_corporate = account_passenger_count + passenger_count

            # if the total number of corp passengeres would exceed the limit, the flight is full
            if total_corporate > self.max_seats_corporate:
                return True

        # otherwise return false
        return False

    def is_past(self):
        return self.arrival < arrow.now().datetime

    def completed_on_time(self):
        """
        Determine if a flight landed on time based on scheduled arrival time and actual arrival time.
        """
        arrival = self.actual_arrival or self.arrival
        difference = arrival - self.arrival
        return abs(difference.total_seconds()) < 900

    def set_plan_restrictions(self, restrictions):
        """
        Takes an iterable to two-tuples of (name, int) and an optional iterable of corporate accounts

        restrictions: iterable of two-tuples (name, days) where `name` is the name of a :class:`billing.models.Plan` and
            `days` is the int number of days the billing plan can reserve in advance
        """

        current_flight_plan_restrictions = []
        for name, days in restrictions:
            p = Plan.objects.get(name__iexact=name)
            fpr, created = FlightPlanRestriction.objects.get_or_create(plan=p, flight=self)
            fpr.days = days
            fpr.save()
            current_flight_plan_restrictions.append(fpr.id)

        self.flightplanrestriction_set.exclude(id__in=current_flight_plan_restrictions).delete()

    def get_minimum_plan(self):
        """
        Finds the minimum plan needed for the account to purchase in order to book this flight today
        Returns: :class:`bllling.models.Plan` or None if the account's plan has no restrictions on this flight
        """
        from billing.models import Plan

        minimum_restriction = None

        delta = self.departure - arrow.now().datetime
        restricted_plans = self.flightplanrestriction_set.filter(days__gte=delta.days).values_list('plan', flat=True)
        non_restricted_plans = Plan.objects.exclude(id__in=restricted_plans).order_by('amount')
        non_restricted_subset = list(non_restricted_plans[:1])
        if non_restricted_subset:
            minimum_restriction = non_restricted_subset[0]

        return minimum_restriction

    def get_flight_reservations(self):
        """
        Returns all the flight reservations for this flight
        """

        return FlightReservation.objects.filter(flight=self, status__in=(FlightReservation.STATUS_RESERVED, FlightReservation.STATUS_CHECKED_IN, FlightReservation.STATUS_COMPLETE))

    def get_pending_flight_reservations(self):
        """
        Returns all the pending flight reservations for this flight
        """

        return FlightReservation.objects.filter(flight=self, status=FlightReservation.STATUS_PENDING)

    def get_anywhere_reservations(self):
        """
        For Anywhere flights, returns all non-cancelled reservations
        Returns:

        """
        return FlightReservation.objects.filter(flight=self, status__in=(FlightReservation.STATUS_RESERVED, FlightReservation.STATUS_CHECKED_IN, FlightReservation.STATUS_COMPLETE, FlightReservation.STATUS_ANYWHERE_PENDING))

    def send_intinerary_update(self, subject=None, message=None, title=None):
        """
        Sends all passengers on the flight an updated flight itinerary email
        """

        for flight_reservation in self.get_flight_reservations():
            flight_reservation.send_reservation_email(subject=subject, message=message, title=title)

    def get_passenger_count(self):
        """
        Returns the number of passengers for this flight as booked
        """
        return Passenger.objects.filter(flight_reservation__flight=self, flight_reservation__status__in=(FlightReservation.STATUS_ANYWHERE_PENDING,FlightReservation.STATUS_RESERVED, FlightReservation.STATUS_CHECKED_IN, FlightReservation.STATUS_COMPLETE, FlightReservation.STATUS_NOSHOW, FlightReservation.STATUS_PARTIALNOSHOW)).count()

    def get_passengers(self, related_fields=None):
        """
        Returns :class:`reservations.models.Passenger` objects for this flight.
        """
        return Passenger.objects.filter(flight_reservation__flight_id=self.id, flight_reservation__status__in=(FlightReservation.STATUS_ANYWHERE_PENDING,FlightReservation.STATUS_RESERVED, FlightReservation.STATUS_CHECKED_IN, FlightReservation.STATUS_COMPLETE, FlightReservation.STATUS_NOSHOW, FlightReservation.STATUS_PARTIALNOSHOW)).select_related('user', 'user__account', 'flight_reservation',)

    def get_pending_reservations(self):
        """
        Returns the number of passengers pending for this flight
        """
        return FlightReservation.objects.filter(flight_id=self.id, status__in=(FlightReservation.STATUS_PENDING)).prefetch_related('passenger_set', 'passenger_set__user', 'passenger_set__user__account',)

    def get_waitlist(self, related_fields=None):
        """
        Returns :class:`reservations.models.FlightWaitlist` objects for this flight.

        related_fields: a list of foreign key fields to include.  Pass an empty list to not retrieve any foreign keys.
            Defaults to ['user', 'user__account']
        """
        from reservations.models import FlightWaitlist
        if related_fields is None:
            related_fields = ['user', 'user__account']

        queryset = FlightWaitlist.objects.filter(flight_id=self.id, status=FlightWaitlist.STATUS_WAITING)
        if related_fields:
            queryset = queryset.select_related(*related_fields)

        return queryset

    def update_plane_seats_available(self):
        """
        Updates the seats available based on the plane seats
        """
        new_seats = self.plane.seats
        if self.pk is None:
            self.seats_available = self.seats_available + (new_seats - self.seats_total)
        else:
            self.seats_available = F('seats_available') + (new_seats - self.seats_total)

        self.seats_total = new_seats

    def save(self, *args, **kwargs):
        """
        When saving, check to see if there is a plane and the seats total is different
        """
        # check if plane seats is different than default or current `seats_total` for flight
        # only change if needed
        if self.plane and self.plane.seats != self.seats_total:
            self.update_plane_seats_available()

        rval = super(Flight, self).save(*args, **kwargs)

        self.refresh_from_db()
        self.refresh_cache()

        return rval

    def load_factor(self):
        """
        Returns the load factor for this flight as seats reserved / total seats
        """
        return (self.seats_total - self.seats_available) / self.seats_total

    # Should be a @property but nothing else in here is :/
    def seats_reserved(self):
        """
        Returns seats_tatal - seats_available.
        """
        return self.seats_total - self.seats_available

    def __unicode__(self):
        return 'Flight %s  %s -> %s on %s' % (self.flight_number, self.origin.code, self.destination.code, self.departure)


class FlightPlanRestriction(models.Model):
    """
    Restrictions per flight based on a plan.

    For example, flight 1234 can be restricted to only allow Express plan members the ability to book the flight X
    number of days from the flight departure time.

    Essentially allows for higher tier plans the ability to book flights before lower tier plans.

    flight: The flight this restriction applies to
    plan: The plan this restriction applies to
    days: The number of days from flight departure that the given plan can book this flight. If days is 0, then this
        plan cannot book this flight.

    """

    flight = models.ForeignKey('flights.Flight')
    plan = models.ForeignKey('billing.Plan')
    days = models.PositiveIntegerField(default=0)

    def __unicode__(self):
        return 'Flight %s - %s - %s' % (self.flight.flight_number, self.plan.name, self.days)


class FlightPlanSeatRestriction(models.Model):
    """
    Seat Restrictions per flight based on a plan.

    For example, flight 1234 can be restricted to only allow Express plan members the ability to book X seats on the
    flight

    flight: The flight this restriction applies to
    plan: The plan this restriction applies to
    seats: The number of seats on the flight that the given plan can book

    """

    flight = models.ForeignKey('flights.Flight')
    plan = models.ForeignKey('billing.Plan')
    seats = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('flight', 'plan',)

    def __unicode__(self):
        return 'Flight %s - %s - %s' % (self.flight.flight_number, self.plan.name, self.seats)


class FlightFeedback(models.Model):
    """
    Feedback on a given flight by an user

    rating: A rating of 1-5, 5 being the best, 1 worst, defaults to 0 for no rating
    comment: Extra feedback, requested if 3 or less stars
    user: the user leaving the feedback
    flight: the flight the user is leaving feedback on
    created: when this feedback was left
    """

    rating = models.SmallIntegerField(default=0)
    comment = models.TextField(blank=True, null=True)
    user = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True)
    flight = models.ForeignKey('flights.Flight', on_delete=models.SET_NULL, null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)

    def __unicode__(self):
        return 'Rating %d from %s' % (self.rating, self.user)


class FlightMessage(models.Model):
    """
    Message update for a flight

    flight: the flight connected with the update
    message: The message body for the flight update
    created: when this message is created
    created_by: the user that created this message, none for system messages if not generated
    """
    '''
    STATUS_CANCELLED = 'C'
    STATUS_ACTIVE = 'A'

    STATUS_CHOICES = (
        (STATUS_CANCELLED, 'Cancelled'),
        (STATUS_ACTIVE, 'Active'),
    )
    '''

    flight = models.ForeignKey('flights.Flight', on_delete=models.SET_NULL, null=True, blank=True, related_name="flight_flight_messages")
    message = models.CharField(max_length=256)
    # TODO: add message details field to display as an extended message on a detail page
    # message_details = models.CharField(max_length=1024, null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True)
    # TODO: add status field for filtering messages
    # status = models.CharField(max_length=1, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    internal = models.BooleanField(default=False, blank=True)

    def send(self, sms_only=False, flightset=None):
        """
        Sends this flight message to all reservations for the given flight via their notification preferences
        """

        # get all the flight reservations for this flight
        flight_reservations = FlightReservation.objects.filter(flight=self.flight, status__in=(FlightReservation.STATUS_RESERVED, FlightReservation.STATUS_CHECKED_IN,FlightReservation.STATUS_ANYWHERE_PENDING))

        for flight_reservation in flight_reservations:
            # get all the passengers on this reservation
            passengers = flight_reservation.all_passengers()

            # for each passenger, send the flight message
            for passenger in passengers:
                userprofile = passenger.userprofile
                # if there is a user object associated with this passenger
                if userprofile is not None:
                    if userprofile.alert_flight_email and not sms_only and userprofile.email:
                        self.send_email(userprofile,flightset)
                    if userprofile.alert_flight_sms and (userprofile.mobile_phone or userprofile.phone):
                        self.send_sms(userprofile)
                else:
                    # get the fake user object and send them an email
                    userprofile = passenger.fake_userprofile()
                    if userprofile.email:
                        self.send_email(userprofile, flightset)


    def send_email(self, userprofile, flightset=None):
        """
        Sends this flight message to the given user as email
        Need special handling for Anywhere cancellations as they have a special template.
        """
        if not userprofile.email:
            return

        if self.flight.is_cancelled():
            if self.flight.flight_type == Flight.TYPE_ANYWHERE and flightset:
                if flightset.is_round_trip:
                    subject = 'Flights %s and %s Canceled' % (flightset.leg1.flight_number, flightset.leg2.flight_number)
                    context = {
                        'leg1': flightset.leg1,
                        'leg2': flightset.leg2,
                        'message': self.message,
                        'title': subject
                    }
                    send_html_email_task.delay('emails/anywhere_flight_cancelled', context, subject, settings.DEFAULT_FROM_EMAIL, [userprofile.email])
                    return
                else:
                    subject = 'Flight %s Canceled' % self.flight.flight_number
            else:
                subject = 'Flight %s Canceled' % self.flight.flight_number
        else:
            subject = 'Flight %s Alert' % self.flight.flight_number

        context = {
            'flight': self.flight,
            'message': self.message
        }

        send_html_email_task.delay('emails/flight_alert', context, subject, settings.DEFAULT_FROM_EMAIL, [userprofile.email])

    def send_sms(self, userprofile):
        """
        Sends this flight message to the given user as SMS
        """
        # try and use their mobile phone if set, otherwise try their default phone
        to = userprofile.mobile_phone or userprofile.phone
        if not to:
            return

        client = TwilioRestClient(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

        client.messages.create(
            body=self.message,
            to=to,
            from_=settings.TWILIO_NUMBER,
        )

    class Meta:
        ordering = ('-created',)

    def __unicode__(self):
        return 'Flight %s: %s' % (self.flight.flight_number, self.message)


auditlog.register(Airport)
auditlog.register(Plane)
auditlog.register(Route)
auditlog.register(RouteTime)
auditlog.register(Flight)


class AlertFlightNotification(models.Model):
    flight = models.ForeignKey('flights.Flight')
    hour_24 = models.BooleanField(default=False)
    hour_1 = models.BooleanField(default=False)
    createdon = models.DateTimeField(blank=True, null=True)


    def send(self,message,subject=None,sms_only=False):
        # get all the flight reservations for this flight
        flight_reservations = FlightReservation.objects.filter(flight=self.flight, status__in=(FlightReservation.STATUS_RESERVED, FlightReservation.STATUS_CHECKED_IN))

        for flight_reservation in flight_reservations:
            # get all the passengers on this reservation
            passengers = flight_reservation.all_passengers()

            # for each passenger, send the flight message
            for passenger in passengers:
                user = passenger.user
                # if there is a user object associated with this passenger
                if user is not None:
                    if user.user_profile.alert_flight_sms and sms_only:
                        self.send_sms(user,message)
                    elif user.user_profile.alert_flight_email and not sms_only:
                        self.send_email(user,message,subject)

    def send_sms(self, user,message):
        """
        Sends this flight alert to the given user as SMS
        """
        # try and use their mobile phone if set, otherwise try their default phone
        to = user.user_profile.mobile_phone or user.user_profile.phone

        client = TwilioRestClient(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

        client.messages.create(
            body=message,
            to=to,
            from_=settings.TWILIO_NUMBER,
        )

    def send_email(self, user,message,subject):

        email = EmailMultiAlternatives(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email])
        try:
            email.send(False)
        except Exception as e:
            logging.exception(e)

