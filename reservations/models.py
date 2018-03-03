import pytz
from django.db import models, transaction
from django.db.models import F, Sum
from django.utils import timezone
from django.utils.functional import cached_property
from django.conf import settings
from django.contrib.auth import get_user_model
from localflavor.us.models import PhoneNumberField
from icalendar import Calendar
import redis
from datetime import timedelta, datetime

from htmlmailer.mailer import send_html_email
from decimal import Decimal, ROUND_HALF_UP
from core.tasks import send_html_email_task

from dateutil.relativedelta import relativedelta


class ReservationError(Exception):
    def __init__(self, message=None, **extra):
        super(ReservationError, self).__init__(message)
        self.extra = extra

    @property
    def detailed_repr(self):
        return '{} {}'.format(self, ','.join(('='.join((k, str(v))) for k, v in self.extra.iteritems())))


class Reservation(models.Model):
    """
    A complete reservation containing 1 or more flight reservations

    account: The account creating the reservation
    status: The status of this entire reservation
        pending: The entire reservation process is still in progress
        reserved: The reservation process is complete and the reservation has been reserved
        cancelled: This entire reservation was cancelled
        complete: The entire reservation is completed
    charge: The associated charge for any cost
    created: When the reservation was created
    created_by: Who created the reservation
    expires: The datetime at which this reservation will expire
    """

    # reservation timeout in seconds
    TIMEOUT = 210 if (settings.STAGING or settings.DEBUG) else 15 * 60

    STATUS_PENDING = 'P'
    STATUS_ANYWHERE_PENDING = 'A'
    STATUS_RESERVED = 'R'
    STATUS_CANCELLED = 'C'
    STATUS_COMPLETE = 'L'

    STATUS_CHOICES = (
        (STATUS_PENDING, 'Pending'),
        (STATUS_ANYWHERE_PENDING, 'Anywhere - Pending'),
        (STATUS_RESERVED, 'Reserved'),
        (STATUS_CANCELLED, 'Cancelled'),
        (STATUS_COMPLETE, 'Complete'),
    )

    account = models.ForeignKey('accounts.Account')
    status = models.CharField(max_length=1, choices=STATUS_CHOICES, default=STATUS_PENDING)
    created = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True)
    expires = models.DateTimeField(blank=True, null=True)
    charge = models.ForeignKey('billing.Charge', on_delete=models.SET_NULL, null=True)

    def send_anywhere_reservation_email(self, to=None, subject=None, message=None, title=None, notify=True, hidePrices=False, reservationOwner=None, passengerName=None):
        title = title or 'RISE ANYWHERE Booking Received'
        flight_reservations = self.flightreservation_set.exclude(status=FlightReservation.STATUS_CANCELLED)

        if flight_reservations.count() == 2:
            total_cost = flight_reservations[0].anywhere_total_cost + flight_reservations[1].anywhere_total_cost
            subtotal = flight_reservations[0].cost + flight_reservations[1].cost
            tax_total = flight_reservations[0].tax  + flight_reservations[1].tax
        else:
            total_cost = flight_reservations[0].anywhere_total_cost
            subtotal = flight_reservations[0].cost
            tax_total = flight_reservations[0].tax


        context = {
            'reservation': self,
            'flight_reservations': flight_reservations,
            'title': title,
            'total_cost': total_cost,
            'subtotal' : subtotal,
            'tax_total' : tax_total
        }
        if message:
            context["message"] = message

        subject = subject or 'Rise Anywhere Reservation'

        if to is None:
            to_emails = Passenger.objects.filter(flight_reservation__reservation=self).exclude(email=None).values_list('email', flat=True)
        else:
            to_emails = to


        attachments = (('reservation.ics', self.ical(to_emails).to_ical(), 'text/calendar'),)

        if hidePrices:
            member_list = [passengerName]
            context.update({'member_list':member_list, "reservation_name": reservationOwner})
            send_html_email_task.delay('emails/anywhere_reservation_noprices', context, subject, settings.DEFAULT_FROM_EMAIL, to_emails, attachments=attachments)

        else:
            passengers = Passenger.objects.filter(email__in=to_emails,flight_reservation__reservation=self).all()
            member_set = set([])
            if passengers is not None:
                for passenger in passengers:
                    name = passenger.get_full_name()
                    member_set.add(name)

            member_list = list(member_set)
            context.update({'member_list':member_list})

            send_html_email_task.delay('emails/anywhere_reservation', context, subject, settings.DEFAULT_FROM_EMAIL, to_emails, attachments=attachments)

        # notify Rise of reservation
        # Because of existing bug with sending emails to multiple addresses at once, in some scenarios we are
        # sending the same notification multiple times to different members but ops only needs one copy of this.
        if notify:
            context = {
                'reservation': self,
                'flight_reservations': flight_reservations,
                'title': 'Anywhere Booking Received:',
                'message': message,
                'account': self.account,
            }

            subject = 'Rise Reservation Notification'

            to_emails = ['ops@iflyrise.com']

            send_html_email_task.delay('emails/admin_reservation', context, subject, settings.DEFAULT_FROM_EMAIL, to_emails)

    def send_reservation_email(self, to=None, subject=None, message=None, title=None):
        """
        Sends the reservation email to all passengers.

        Includes the iCal attachment.

        to: If to is provided as a list of emails, send to those emails only.
        """
        flight_reservations = self.flightreservation_set.exclude(status=FlightReservation.STATUS_CANCELLED)

        if flight_reservations[0].flight.flight_type == 'A':
            return self.send_anywhere_reservation_email(to, subject, message, title)

        title = title or 'Booking Confirmation'

        context = {
            'reservation': self,
            'flight_reservations': flight_reservations,
            'title': title,
            'message': message,
        }

        subject = subject or 'Rise Reservation'

        if to is None:
            to_emails = Passenger.objects.filter(flight_reservation__reservation=self).exclude(email=None).values_list('email', flat=True)
        else:
            to_emails = to

        passengers = Passenger.objects.filter(email__in=to_emails,flight_reservation__reservation=self).all()
        member_list = []
        if passengers is not None:
            for passenger in passengers:
                member_list.append(passenger.get_full_name())

        context.update({'member_list':member_list})

        attachments = (('reservation.ics', self.ical(to_emails).to_ical(), 'text/calendar'), ('invite.ics', self.ical(to_emails).to_ical(), 'application/ics; name="invite.ics"'))

        send_html_email_task.delay('emails/reservation', context, subject, settings.DEFAULT_FROM_EMAIL, to_emails, attachments=attachments)

        # notify Rise of reservation

        context = {
            'reservation': self,
            'flight_reservations': flight_reservations,
            'title': 'Booking Confirmed:',
            'message': message,
            'account': self.account,
        }

        subject = 'Rise Reservation Notification'

        to_emails = ['ops@iflyrise.com']

        send_html_email_task.delay('emails/admin_reservation', context, subject, settings.DEFAULT_FROM_EMAIL, to_emails)

    def ical(self, attendees=None):
        """
        Creates and returns the iCal file for this reservation
        """
        cal = Calendar()
        cal.add('version', '2.0')
        cal.add('method', 'REQUEST')
        cal.add('CALSCALE', 'GREGORIAN')

        flight_reservations = self.flightreservation_set.exclude(status=FlightReservation.STATUS_CANCELLED)
        for flight_reservation in flight_reservations:
            event = flight_reservation.flight.ical_event(attendees)
            cal.add_component(event)

        return cal

    def reserve(self, send_email=True):
        """
        Officially reserve this reservation
        """
        self.status = Reservation.STATUS_RESERVED
        self.expires = None
        self.save()

        self.flightreservation_set.all().update(status=FlightReservation.STATUS_RESERVED)

        if send_email:
            self.send_reservation_email()

    def is_cancelable(self):
        """
        Returns True if this can be cancelled
        """
        return self.status in (Reservation.STATUS_ANYWHERE_PENDING, Reservation.STATUS_PENDING, Reservation.STATUS_RESERVED)

    def cancel(self, try_void_charge=False):
        """
        Cancel's a reservation

        If status is pending, free resources and delete

        If status is reserved, keep a reference to it for account purposes

        #Reservations with charges that are Authorized or Submitted for settlement need to be voided at the reservation level,
        #they won't  have refunded at the flight_reservation level
        """
        if self.is_cancelable():
            for flight_reservation in self.flightreservation_set.all():
                flight_reservation.cancel()

            if self.status == Reservation.STATUS_PENDING:
                self.delete()
            else:
                self.status = Reservation.STATUS_CANCELLED
                self.save()
            if try_void_charge:
                if self.charge and not self.charge.refunded:
                    self.charge.void("Cancel Reservation %s" % self.pk, user=None)


    def renew(self):
        """
        Renews a resevations resetting expiration time
        """
        Reservation.objects.filter(id=self.id).update(expires=timezone.now() + timedelta(seconds=Reservation.TIMEOUT))

    def expired(self):
        """
        Returns true if this reservation has expired
        """
        return timezone.now() > self.expires

    def seconds_remaining(self):
        """
        Returns the number of seconds left before this reservation expires
        """
        delta = self.expires - timezone.now()
        if delta.seconds < 0:
            return 0

        return delta.seconds

    def requires_payment(self):
        """
        Returns True if this reservation requires a payment due to the need to buy a pass or flight surcharges.
        """
        if self.total_buy_pass_count > 0:
            return True

        if self.total_buy_companion_pass_count > 0:
            return True

        if self.total_surcharge() > 0:
            return True

        return False

    @cached_property
    def total_buy_pass_count(self):
        """
        Return the total number of save my seat passes needed to buy for this reservation
        """
        return self.flightreservation_set.all().aggregate(Sum('buy_pass_count'))['buy_pass_count__sum']

    @cached_property
    def total_buy_companion_pass_count(self):
        """
        Return the total number of companion passes needed to buy for this reservation
        """
        return self.flightreservation_set.all().aggregate(Sum('buy_companion_pass_count'))['buy_companion_pass_count__sum']

    def total_pass_amount(self):
        """
        Returns the total amount to be paid for passes
        """
        return self.total_buy_pass_count * settings.PASS_COST

    def total_companion_pass_amount(self):
        """
        Returns the total amount to be paid for companion passes
        """
        return self.total_buy_companion_pass_count * settings.COMPANION_PASS_COST

    def total_surcharge(self):
        """
        Returns the total amount of surcharges for flights booked
        """
        return self.flightreservation_set.all().aggregate(Sum('flight__surcharge'))['flight__surcharge__sum']

    def subtotal_amount(self):
        """
        Returns the total amount for both companion and save my seat passes and surcharges.
        """
        return self.total_pass_amount() + self.total_companion_pass_amount() + self.total_surcharge()

    def subtotal_amount_fet_tax(self, tax_percentage=settings.FET_TAX):
        """
        Returns the FET tax for the total amount
        """
        return (self.subtotal_amount() * tax_percentage).quantize(Decimal('0.00'), rounding=ROUND_HALF_UP)

    def total_amount(self):
        """
        Returns the total amount including tax
        """
        return (self.subtotal_amount() + self.subtotal_amount_fet_tax())

    def set_anywhere_other_cost(self, flightset):
        #updates the other charges & tax rate fields.
        for fr in self.flightreservation_set.all():
            if fr.flight_id == flightset.leg1.id:
                fr.other_charges = flightset.leg1.anywhere_details.other_cost
            else:
                fr.other_charges = flightset.leg2.anywhere_details.other_cost
            fr.tax = (fr.cost + fr.other_charges) * settings.FET_TAX
            fr.save()

    def calculate_anywhere_seat_cost(self):
        return sum(fr.cost for fr in self.flightreservation_set.all())

    def calculate_anywhere_other_charges(self):
        return sum(fr.other_charges for fr in self.flightreservation_set.all())

    def calculate_anywhere_tax(self):
        return sum(fr.tax for fr in self.flightreservation_set.all())

    def calculate_anywhere_totalcost(self):
        """
        Calculate and return the summed cost of related FlightRequests.

        Used for Anywhere requests, which are incompatible with all of the other decimal fields on this object.

        Total cost is now calculated from sum of line items on flight reservations, since each reservation will correctly
        save its own total cost.
        """
        return sum(fr.anywhere_total_cost for fr in self.flightreservation_set.all())

    def calculate_anywhere_refund(self):
        return sum(fr.anywhere_refund_due for fr in self.flightreservation_set.filter(anywhere_refund_paid=False).all())

    def calculate_final_adjusted_seat_cost(self):
        return sum(fr.final_adjusted_seat_cost for fr in self.flightreservation_set.all())

    def calculate_final_adjusted_tax(self):
        return sum(fr.final_adjusted_tax for fr in self.flightreservation_set.all())

    def calculate_final_adjusted_total(self):
        return self.calculate_final_adjusted_seat_cost() + self.calculate_final_adjusted_tax() + self.calculate_anywhere_other_charges()

    @property
    def flight_numbers(self):
        list = ",".join(str(flightres.flight.flight_number) for flightres in self.flightreservation_set.all())
        return list

    def __unicode__(self):
        return 'Reservation %d' % self.id


class FlightReservation(models.Model):
    """
    A reservation for an individual flight

    reservation: Reference to the entire reservation
    flight: The flight this reservation is for
    status: The status of this flight reservation
        pending: The user is still completing the reservation process
        reserved: The user has completed the reservation process and these reservations are reserved
        checked in: The user has checked in on their flight
        cancelled: The user has cancelled this flight reservation
        complete: The flight is complete and therefore this reservation is complete as well
    passenger_count: The number of passengers on this flight reservation
    pass_count: The number of account passes used to book this reservation
    complimentary_pass_count: The number of passes used for this flight reservation that were complimentary. These will
        not get added back to the account when this flight is complete.
    companion_pass_count: The number of account companion passes used to book this reservation.
    complimentary_companion_pass_count: The number of complimentary companion pass counts used to book this reservation.
    buy_pass_count: The number of passes to be paid for for this flight. These will not get added back to the account
        when this flight is complete.
    buy_companion_pass_count: The number of companion passes that will need to be bought for this flight reservation.
    created: When this reservation was created
    created_by: Who created this reservation


    date_cancelled: Date this reservation was created (optional)
    cancelled_by: Who cancelled this reservation (optional)
    """

    STATUS_PENDING = 'P'
    STATUS_ANYWHERE_PENDING = 'A'
    STATUS_RESERVED = 'R'
    STATUS_CHECKED_IN = 'I'
    STATUS_CANCELLED = 'C'
    STATUS_COMPLETE = 'L'
    STATUS_NOSHOW = 'N'
    STATUS_PARTIALNOSHOW = 'Q'

    STATUS_CHOICES = (
        (STATUS_PENDING, 'Pending'),
        (STATUS_ANYWHERE_PENDING,'Anywhere - Pending Confirmation'),
        (STATUS_RESERVED, 'Reserved'),
        (STATUS_CHECKED_IN, 'Checked-In'),
        (STATUS_CANCELLED, 'Cancelled'),
        (STATUS_COMPLETE, 'Complete'),
        (STATUS_NOSHOW, 'No-Show'),
        (STATUS_PARTIALNOSHOW, 'Partial No-Show')
    )

    reservation = models.ForeignKey('reservations.Reservation')
    flight = models.ForeignKey('flights.Flight')
    status = models.CharField(max_length=1, choices=STATUS_CHOICES, default=STATUS_PENDING)
    passenger_count = models.PositiveIntegerField(default=1)
    pass_count = models.PositiveIntegerField(default=0)
    complimentary_pass_count = models.PositiveIntegerField(default=0)
    companion_pass_count = models.PositiveIntegerField(default=0)
    complimentary_companion_pass_count = models.PositiveIntegerField(default=0)
    buy_pass_count = models.PositiveIntegerField(default=0)
    buy_companion_pass_count = models.PositiveIntegerField(default=0)
    cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    other_charges = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    final_adjusted_seat_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    final_adjusted_tax = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    created = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True)

    date_cancelled = models.DateTimeField(null=True, blank=True)
    cancelled_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name="cancelled_flight_reservations")
    cancellation_reason = models.CharField(max_length=50, null=True)

    # these fields are for Rise Anywhere flights that have decreased in price since the reservation was created.
    # refunds are sent when the flight fills or completes, whichever comes first.
    anywhere_refund_due = models.DecimalField(max_digits=10, decimal_places=2, default=0, null=False)
    anywhere_refund_paid = models.BooleanField(default=False, null=False)

    def send_reservation_email(self, to=None, subject=None, message=None, title=None):
        """
        Sends the reservation email to all passengers.

        Includes the iCal attachment.

        to: If to is provided as a list of emails, send to those emails only.
        """
        title = title or 'Booking Confirmation'
        context = {
            'reservation': self.reservation,
            'flight_reservations': [self],
            'message': message,
            'title': title,
        }

        subject = subject or 'Rise Reservation'

        if to is None:
            to_emails = Passenger.objects.filter(flight_reservation=self).exclude(email=None).values_list('email', flat=True)
        else:
            to_emails = to

        passengers = Passenger.objects.filter(email__in=to_emails,flight_reservation__reservation=self.reservation).all()
        member_list = []
        if passengers is not None:
            for passenger in passengers:
                member_list.append(passenger.get_full_name())

        context.update({'member_list':member_list})
        attachments = (('reservation.ics', self.ical().to_ical(), 'text/calendar'),)

        send_html_email_task.delay('emails/reservation', context, subject, settings.DEFAULT_FROM_EMAIL, to_emails, attachments=attachments)

    def ical(self):
        """
        Creates and returns the iCal file for this reservation
        """
        cal = Calendar()
        cal.add('version', '2.0')
        cal.add('method', 'REQUEST')
        cal.add('CALSCALE', 'GREGORIAN')

        event = self.flight.ical_event()
        cal.add_component(event)

        return cal

    def add_passenger(self, userprofile, companion=False):
        """
        Add a given user as a passenger on this flight reservation
        """
        phone = ''
        date_of_birth = None
        try:
            phone = userprofile.phone
            date_of_birth = userprofile.date_of_birth
        except AttributeError:
            pass

        passenger = Passenger.objects.create(
            flight_reservation=self,
            userprofile=userprofile,
            companion=companion,
            first_name=userprofile.first_name,
            last_name=userprofile.last_name,
            email=userprofile.email,
            phone=phone,
            date_of_birth=date_of_birth,
        )

        return passenger

    @cached_property
    def primary_passenger(self):
        """
        Returns the primary passenger on this flight reservation
        AMF-RISE 289 If there is no member then it will return the first companion
        But if there is a member the member goes first.
        """
        member = next(iter(self.passenger_set.filter(companion=False).select_related('userprofile', 'userprofile__account')), None)
        if member:
            return member
        companion_only = next(iter(self.passenger_set.select_related('userprofile', 'userprofile__account')), None)
        return companion_only

    def get_other_passenger_count(self):
        return self.passenger_count - 1

    def has_companions(self):
        """
        Returns true if this flight reservation has companions
        """
        return self.passenger_set.filter(companion=True).exists()

    def get_companions(self):
        """
        Returns the companions on this flight reservation
        """
        return self.passenger_set.filter(companion=True).select_related('userprofile', 'userprofile__account')

    def get_companion_count(self):
        """
        Returns the count for the companions on this flight reservation
        """
        return self.passenger_set.filter(companion=True).count()

    def all_passengers(self):
        """
        Returns all passengers on this flight reservation
        """
        return self.passenger_set.all().select_related('userprofile', 'userprofile__account')

    def clear_companions(self):
        """
        Remove companions from this flight reservation
        """
        self.passenger_set.filter(companion=True).delete()

    def pass_amount(self):
        """
        Return the amount for the passes
        """
        return self.buy_pass_count * settings.PASS_COST

    def companion_pass_amount(self):
        """
        returns the amount for the companion passes
        """
        return self.buy_companion_pass_count * settings.COMPANION_PASS_COST

    def is_cancelable(self):
        """
        Returns true if this reservation can be cancelled
        """
        if self.status not in (FlightReservation.STATUS_PENDING, FlightReservation.STATUS_RESERVED, FlightReservation.STATUS_ANYWHERE_PENDING):
            return False

        return self.flight.status in (self.flight.STATUS_ON_TIME, self.flight.STATUS_DELAYED)

    def is_cancelled(self):
        """
        Returns True if this reservation is cancelled
        """
        return self.status == FlightReservation.STATUS_CANCELLED

    @property
    def anywhere_total_cost(self):
        return self.cost + self.tax + self.other_charges

    def free_one_seat(self, userprofile):
        """
        Frees ONE seat from the reservation:
        Returns:

        """
        from flights.models import Flight

        r = redis.from_url(settings.REDIS_URL)
        seats_available_key = self.flight.cache_key('seats_available')
        companion_count=0
        # is this user a companion - no companions on Anywhere flights
        # if they don't have a user account they are a companion for non-anywhere flights
        if not userprofile.user  and self.flight.flight_type != 'A':
            companion_count = 1
        # or if they have a user but don't have the booking privilege they are a companion for non-anywhere flights
        elif userprofile.user and not userprofile.user.has_perm("accounts.can_book_flights") and self.flight.flight_type !='A':
            companion_count = 1

        with r.pipeline() as pipe:
            while 1:
                try:
                    # put a WATCH on the key that holds our sequence value
                    pipe.watch(seats_available_key)
                    # after WATCHing, the pipeline is put into immediate execution
                    # mode until we tell it to start buffering commands again.
                    # this allows us to get the current value of our sequence
                    current_value = pipe.get(seats_available_key) or self.flight.seats_available
                    next_value = int(current_value) + 1
                    # now we can put the pipeline back into buffered mode with MULTI
                    pipe.multi()
                    pipe.set(seats_available_key, next_value)
                    # and finally, execute the pipeline (the set command)
                    pipe.execute()
                    # if a WatchError wasn't raised during execution, everything we just did happened atomically.
                    # update databsae with seat counts
                    Flight.objects.filter(id=self.flight.id).update(seats_available=F('seats_available') + 1, seats_companion=F('seats_companion') + companion_count)

                    break
                except redis.WatchError:
                    # another client must have changed our key between
                    # the time we started WATCHing it and the pipeline's execution.
                    # our best bet is to just retry.
                    continue


    def free_seats(self):
        """
        Free the seats on the flight associated with this flight reservation
        """
        from flights.models import Flight

        r = redis.from_url(settings.REDIS_URL)
        seats_available_key = self.flight.cache_key('seats_available')
        companion_count = self.passenger_count - 1

        with r.pipeline() as pipe:
            while 1:
                try:
                    # put a WATCH on the key that holds our sequence value
                    pipe.watch(seats_available_key)
                    # after WATCHing, the pipeline is put into immediate execution
                    # mode until we tell it to start buffering commands again.
                    # this allows us to get the current value of our sequence
                    current_value = pipe.get(seats_available_key) or self.flight.seats_available
                    next_value = int(current_value) + self.passenger_count
                    # now we can put the pipeline back into buffered mode with MULTI
                    pipe.multi()
                    pipe.set(seats_available_key, next_value)
                    # and finally, execute the pipeline (the set command)
                    pipe.execute()
                    # if a WatchError wasn't raised during execution, everything we just did happened atomically.
                    # update databsae with seat counts
                    Flight.objects.filter(id=self.flight.id).update(seats_available=F('seats_available') + self.passenger_count, seats_companion=F('seats_companion') - companion_count)
                    break
                except redis.WatchError:
                    # another client must have changed our key between
                    # the time we started WATCHing it and the pipeline's execution.
                    # our best bet is to just retry.
                    continue

    def free_account_passes(self, complimentary=False):
        """
        Free any account passes associated with this flight reservation

        If complimentary is True, it will also restore any complimentary passes (ex if you cancel the flight
            reservation you get those back).
        """
        from accounts.models import Account

        r = redis.from_url(settings.REDIS_URL)

        available_passes_key = self.reservation.account.get_cache_key('available_passes')
        complimentary_passes_key = self.reservation.account.get_cache_key('complimentary_passes')
        available_companion_passes_key = self.reservation.account.get_cache_key('available_companion_passes')
        complimentary_companion_passes_key = self.reservation.account.get_cache_key('complimentary_companion_passes')

        with r.pipeline() as pipe:
            while 1:
                try:
                    # put a WATCH on the key that holds our sequence value
                    pipe.watch(available_passes_key)
                    pipe.watch(available_companion_passes_key)
                    if complimentary:
                        pipe.watch(complimentary_passes_key)
                        pipe.watch(complimentary_companion_passes_key)
                    # after WATCHing, the pipeline is put into immediate execution
                    # mode until we tell it to start buffering commands again.
                    # this allows us to get the current value of our sequence
                    available_passes = int(pipe.get(available_passes_key) or self.reservation.account.available_passes)
                    available_passes += self.pass_count

                    available_companion_passes = int(pipe.get(available_companion_passes_key) or self.reservation.account.available_companion_passes)
                    available_companion_passes += self.companion_pass_count

                    if complimentary:
                        complimentary_passes = int(pipe.get(complimentary_passes_key) or self.reservation.account.complimentary_passes)
                        complimentary_passes += self.complimentary_pass_count

                        complimentary_companion_passes = int(pipe.get(complimentary_companion_passes_key) or self.reservation.account.complimentary_companion_passes)
                        complimentary_companion_passes += self.complimentary_companion_pass_count

                    # now we can put the pipeline back into buffered mode with MULTI
                    pipe.multi()
                    pipe.set(available_passes_key, available_passes)
                    pipe.set(available_companion_passes_key, available_companion_passes)

                    if complimentary:
                        pipe.set(complimentary_passes_key, complimentary_passes)
                        pipe.set(complimentary_companion_passes_key, complimentary_companion_passes)

                    # and finally, execute the pipeline (the set command)
                    pipe.execute()
                    # if a WatchError wasn't raised during execution, everything we just did happened atomically.

                    # update databsae with pass counts
                    # Account.objects.filter(id=self.reservation.account.id).update(
                    #     available_passes=F('available_passes') + self.pass_count,
                    #     available_companion_passes=F('available_companion_passes') + self.companion_pass_count,
                    # )
                    for account in Account.objects.filter(id=self.reservation.account.id):
                        account.available_passes = F('available_passes') + self.pass_count
                        account.available_companion_passes = F('available_companion_passes') + self.companion_pass_count
                        account.save()

                    # ensure available_passes never exceeds the account's pass count
                    # Account.objects.filter(id=self.reservation.account.id, available_passes__gt=F('pass_count')).update(available_passes=F('pass_count'))
                    for account in Account.objects.filter(id=self.reservation.account.id, available_passes__gt=F('pass_count')):
                        account.available_passes = F('pass_count')
                        account.save()

                    # ensure available_companion_passes never exceeds the account's companion pass count
                    # Account.objects.filter(id=self.reservation.account.id, available_companion_passes__gt=F('companion_pass_count')).update(available_companion_passes=F('companion_pass_count'))
                    for account in Account.objects.filter(id=self.reservation.account.id, available_companion_passes__gt=F('companion_pass_count')):
                        account.available_companion_passes = F('companion_pass_count')
                        account.save()

                    # if complimentary:
                    #     Account.objects.filter(id=self.reservation.account.id).update(
                    #         complimentary_passes=F('complimentary_passes') + self.complimentary_pass_count,
                    #         complimentary_companion_passes=F('complimentary_companion_passes') + self.complimentary_companion_pass_count
                    #     )
                    for account in Account.objects.filter(id=self.reservation.account.id):
                        account.complimentary_passes = F('complimentary_passes') + self.complimentary_pass_count
                        account.complimentary_companion_passes = F('complimentary_companion_passes') + self.complimentary_companion_pass_count
                        account.save()

                    break
                except redis.WatchError:
                    # another client must have changed our key between
                    # the time we started WATCHing it and the pipeline's execution.
                    # our best bet is to just retry.
                    continue


    def free_account_passes_for_passenger(self, userprofile):
        """
        Free any account passes associated with this passenger on the flight reservation
        including complimentary passes
        """
        from accounts.models import Account

        r = redis.from_url(settings.REDIS_URL)
        if userprofile.user and userprofile.user.has_perm("accounts.can_book_flights"):
            companion=False
        else:
            companion=True

        if companion==True:
            available_companion_passes_key = self.reservation.account.get_cache_key('available_companion_passes')
            complimentary_companion_passes_key = self.reservation.account.get_cache_key('complimentary_companion_passes')
        else:
            available_passes_key = self.reservation.account.get_cache_key('available_passes')
            complimentary_passes_key = self.reservation.account.get_cache_key('complimentary_passes')

        with r.pipeline() as pipe:
            while 1:
                try:
                    # put a WATCH on the key that holds our sequence value
                    if companion==True:
                        pipe.watch(available_companion_passes_key)
                        pipe.watch(complimentary_companion_passes_key)

                        available_companion_passes = int(pipe.get(available_companion_passes_key) or self.reservation.account.available_companion_passes)
                        available_companion_passes += self.companion_pass_count

                        complimentary_companion_passes = int(pipe.get(complimentary_companion_passes_key) or self.reservation.account.complimentary_companion_passes)
                        complimentary_companion_passes += self.complimentary_companion_pass_count

                        # now we can put the pipeline back into buffered mode with MULTI
                        pipe.multi()
                        pipe.set(available_companion_passes_key, available_companion_passes)

                        pipe.set(complimentary_companion_passes_key, complimentary_companion_passes)

                        # and finally, execute the pipeline (the set command)
                        pipe.execute()
                        # if a WatchError wasn't raised during execution, everything we just did happened atomically.
                        # free passes in reverse order to usage priority
                        if self.buy_companion_pass_count > 0:
                            self.buy_companion_pass_count -= 1
                            self.save()
                        elif self.complimentary_companion_pass_count > 0:
                            self.complimentary_companion_pass_count -=1
                            userprofile.account.complimentary_companion_passes = F('complimentary_companion_passes') + 1
                            self.save()
                            userprofile.account.save()
                        elif self.companion_pass_count > 0:
                            userprofile.account.available_companion_passes = F('companion_pass_count') + 1
                            self.companion_pass_count -=1
                            self.save()
                            userprofile.account.save()

                    else:
                        pipe.watch(available_passes_key)
                        pipe.watch(complimentary_passes_key)
                        # after WATCHing, the pipeline is put into immediate execution
                        # mode until we tell it to start buffering commands again.
                        # this allows us to get the current value of our sequence

                        # after WATCHing, the pipeline is put into immediate execution
                        # mode until we tell it to start buffering commands again.
                        # this allows us to get the current value of our sequence
                        available_passes = int(pipe.get(available_passes_key) or self.reservation.account.available_passes)
                        available_passes += self.pass_count
                        complimentary_passes = int(pipe.get(complimentary_passes_key) or self.reservation.account.complimentary_passes)
                        complimentary_passes += self.complimentary_pass_count

                        pipe.multi()
                        pipe.set(available_passes_key, available_passes)
                        pipe.set(complimentary_passes_key, complimentary_passes)

                        # and finally, execute the pipeline (the set command)
                        pipe.execute()

                        # free passes in reverse order to usage priority
                        if self.buy_pass_count > 0:
                            self.buy_pass_count -=1
                            self.save()
                        elif self.complimentary_pass_count > 0:
                            userprofile.account.complimentary_passes = F('complimentary_passes') + 1
                            self.complimentary_pass_count -= 1
                            userprofile.account.save()
                            self.save()
                        elif self.pass_count > 0:
                            userprofile.account.available_passes = F('available_passes') + 1
                            self.pass_count -=1
                            userprofile.account.save()
                            self.save()



                    break
                except redis.WatchError:
                    # another client must have changed our key between
                    # the time we started WATCHing it and the pipeline's execution.
                    # our best bet is to just retry.
                    continue

    def remove_passenger(self, userprofile, refund_eligible=False):
        """
        Removes a single passenger from a reservation without cancelling the entire reservation.
        Frees their seat in Redis + database
        Return passes as appropriate.
        Args:
            userprofile:
            refund_eligible:  refunds the user's portion of the reservation previously paid.

        Returns:

        """
        if self.is_cancelable():

            with transaction.atomic():
                fees = 0
                refund_error = ''
                 # if there was a charge associated with this reservation refund it
                 # have to refund before freeing passes or fees calculation is wrong
                if self.reservation.charge is not None and refund_eligible:
                    if self.flight.flight_type == "A":
                        #currently we are disallowing refunds for Anywhere flights from this process so this won't be hit.
                        #fees for anywhere flights will be based on spot cost paid
                        spot_cost = self.flight.anywhere_details.per_seat_cost
                        if userprofile.user and userprofile.user.id == self.flight.anywhere_details.anywhere_request.created_by_id:
                            other_cost = self.flight.anywhere_details.other_cost
                        else:
                            other_cost = 0
                        tax = (spot_cost + other_cost) * settings.FET_TAX
                        fees = spot_cost + tax + other_cost
                    else:
                        # get the fees associated with this reservation
                        fees = self.fees_for_single_passenger(userprofile.user)

                    # if the fees on a reservation were overridden, then it is possible that the reservation thinks that
                    # they bought passes / paid surcharge but they actually did not.  If they weren't actually
                    # charged as much as the system thinks they should have paid, just show a message saying a refund
                    # could not be processed automatically.
                    if fees <= self.reservation.charge.refund_amount_remaining():
                        from billing.models import GenericBillingException
                        try:
                            self.reservation.charge.refund(fees, 'passenger removed from flight reservation', None)
                        except GenericBillingException as gbe:
                            refund_error = gbe.message
                    else:
                        refund_error = 'The estimated refund amount is more than the actual amount charged on this reservation so no refund was processed.'
                # free ONE seat on the plane
                self.free_one_seat(userprofile)


                # free account passes including complimentary ones since it was cancelled
                if self.flight.flight_type != "A":
                    self.free_account_passes_for_passenger(userprofile)

                passenger = Passenger.objects.filter(flight_reservation_id=self.id, userprofile_id=userprofile.id).first()
                passenger.delete()

                self.passenger_count -= 1
                self.save()

                # notifying Rise of the cancelation
                flight_reservations = [self, ]
                if refund_eligible and fees > 0:
                    if refund_error == '':
                        message = 'A passenger, %s,  has been removed from this reservation. Charges of $%s have been refunded.' % (userprofile.get_full_name(), fees)
                    else:
                        message = 'A passenger, %s,  has been removed from this reservation. %s' % (userprofile.get_full_name(), refund_error)

                else:
                    message = 'A passenger, %s,  has been removed from this reservation.'   % (userprofile.get_full_name())
                context = {
                    'reservation': self.reservation,
                    'flight_reservations': flight_reservations,
                    'title': 'Passenger %s removed from booking:' % userprofile.get_full_name(),
                    'message': message,
                    'account': self.reservation.account
                }
                subject = 'Rise Reservation Passenger Removed'
                to_emails = ['ops@iflyrise.com']
                send_html_email_task.delay('emails/admin_reservation_cancel', context, subject, settings.DEFAULT_FROM_EMAIL, to_emails)


    def is_refund_eligible(self):
        timedelta_diff = self.flight.departure-timezone.now()
        hours_left = timedelta_diff.total_seconds()/3600
        if self.flight.flight_type != "A":
            return True
        elif hours_left < settings.CANCELLATION_WINDOW_ENDTIME:
            return False
        else:
            return True


    def cancel(self, user=None, flight_cancelled=False, refund_eligible=False):
        """
        Cancels a flight reservation.

        Free seats in Redis as well as database.

        If pending, just delete, otherwise set status to cancelled.

        flight_cancelled is used when the entire flight is cancelled and we need to make sure to reverse charges.
        """
        if self.is_cancelable():
            with transaction.atomic():

                 # if there was a charge associated with this reservation refund it
                 # have to refund before freeing passes or fees calculation is wrong
                if self.reservation.charge is not None:
                    if self.flight.flight_type == "A":
                        #fees are calculated differently than with regular flights
                        fees = self.anywhere_total_cost
                    else:
                        # get the fees associated with this reservation
                        fees = self.fees(include_tax=True)

                    #if the flight is not anywhere or if the flight is anywhere and the departure is greater than 24 hours then
                    #refunds are eligible
                    if refund_eligible and self.is_refund_eligible():
                        self.reservation.charge.refund(fees, 'flight reservation cancelled', None)

                # free the seats on the plane
                self.free_seats()

                # free account passes including complimentary ones since it was cancelled
                self.free_account_passes(complimentary=True)

                # if this is pending, just delete it since it was never a real reservation
                if self.status == FlightReservation.STATUS_PENDING:
                    self.delete()
                else:  # otherwise set to cancelled and save
                    self.status = FlightReservation.STATUS_CANCELLED
                    self.date_cancelled = timezone.now()
                    if user:
                        self.cancelled_by = user
                        if not self.cancellation_reason:
                            self.cancellation_reason = 'Reservation cancelled by member'
                    elif self.cancellation_reason is None:
                        self.cancellation_reason = 'Flight cancelled by RISE'
                    self.save()

                    # notifying Rise of the cancelation
                    flight_reservations = [self, ]
                    context = {
                        'reservation': self.reservation,
                        'flight_reservations': flight_reservations,
                        'title': 'Booking Cancelled:',
                        'message': None,
                        'account': self.reservation.account,
                    }
                    subject = 'Rise Reservation Cancellation'
                    to_emails = ['ops@iflyrise.com']
                    send_html_email_task.delay('emails/admin_reservation_cancel', context, subject, settings.DEFAULT_FROM_EMAIL, to_emails)
        elif flight_cancelled:
            self.status = FlightReservation.STATUS_CANCELLED

            self.date_cancelled = timezone.now()
            if user:
                self.cancelled_by = user
                if self.cancellation_reason == None:
                    self.cancellation_reason = 'Reservation cancelled by member'
            elif self.cancellation_reason is None:
                self.cancellation_reason = 'Flight cancelled by RISE'
            self.save()

            #flight was cancelled so we have to refund if the flight is refund eligible
            if self.reservation.charge is not None and refund_eligible:
                #fees are calculated differently than with regular flights
                if self.flight.flight_type == "A":
                    fees = self.anywhere_total_cost
                else:
                    # get the fees associated with this reservation
                    fees = self.fees(include_tax=True)

                #if the flight is not anywhere or if the flight is anywhere and the departure is greater than 24 hours then
                #refunds are eligible
                if self.is_refund_eligible():
                    self.reservation.charge.refund(fees, 'Flight reservation %s / Flight # %s cancelled' % (self.id, self.flight.flight_number), None)

    def refund_only(self):
        if self.reservation.charge is not None:
                #fees are calculated differently than with regular flights
                if self.flight.flight_type == "A":
                    fees = self.anywhere_total_cost
                else:
                    # get the fees associated with this reservation
                    fees = self.fees(include_tax=True)
                #if the flight is not anywhere or if the flight is anywhere and the departure is greater than 24 hours then
                #refunds are eligible
                if self.is_refund_eligible():
                    self.reservation.charge.refund(fees, 'Flight reservation %s / Flight # %s cancelled' % (self.id, self.flight.flight_number), None)

    def fees_for_single_passenger(self, user):
        """
        Calculates the fees needed to refund when a single passenger is removed from a reservation.
        (buy_pass or companion_pass if applicable) + tax
        surcharge is currently only being charged 1x per reservation so don't refund that here.
        it will refund if entire reservation is cancelled.
        Args:
            user:
        Returns:

        """
        # user might not exist now, if it is a dependent companion it won't have a login.

        if user and user.has_perm("account.can_book_flights"):
            if self.buy_pass_count > 0:
                return (settings.PASS_COST * settings.FET_TAX) + settings.PASS_COST
        else:
            if self.companion_pass_count > 0:
                return (settings.COMPANION_PASS_COST * settings.FET_TAX) + settings.COMPANION_PASS_COST

        return 0

    def fees(self, include_tax):
        """
        Determine the fees associated with this reservation
        """
        total = 0

        if self.flight.surcharge:
            total += self.flight.surcharge

        if self.buy_companion_pass_count:
            total += settings.COMPANION_PASS_COST * self.buy_companion_pass_count

        if self.buy_pass_count:
            total += settings.PASS_COST * self.buy_pass_count

        if include_tax:
            total += (total * settings.FET_TAX)

        return total

    def check_in(self):
        """
        Checks in a flight reservation.
        """
        with transaction.atomic():
            if not self.status == FlightReservation.STATUS_CHECKED_IN:
                self.status = FlightReservation.STATUS_CHECKED_IN
                self.save()

    def partialnoshow(self):
        """
        Marks a flight reservation as partial no-show.
        """
        with transaction.atomic():
            if not self.status == FlightReservation.STATUS_PARTIALNOSHOW:
                self.status = FlightReservation.STATUS_PARTIALNOSHOW
                self.save()

    def noshow(self):
        """
        Marks a flight reservation as partial no-show.
        """
        with transaction.atomic():
            if not self.status == FlightReservation.STATUS_NOSHOW:
                self.status = FlightReservation.STATUS_NOSHOW
                self.save()

    def complete(self):
        """
        Marks a flight reservation as complete.
        """
        with transaction.atomic():
            if not self.status == FlightReservation.STATUS_COMPLETE:
                self.status = FlightReservation.STATUS_COMPLETE
                self.save()

    def __unicode__(self):
        return 'FlightReservation for Flight %s' % self.flight.flight_number


class Passenger(models.Model):
    """
    A passenger for a given flight reservation

    flight_reservation: The flight reservation this passenger is on
    userprofile:  Person who will be flying
    user: The user account for this passenger. Optional as the passenger could be manually added for a promotional flight, and could be a dependent companion
    companion: True if this passenger is a companion on this flight
    first_name: The passenger's first name
    last_name: The passenger's last name
    email: The passenger's email in case we need to send a notification about this flight reservation
    phone: The passenger's phone in case we need to get in touch about this flight reservation
    date_of_birth: The passenger's date of birth for background check
    background_status: The status of this passenger's background check
    """

    BACKGROUND_NOT_STARTED = 0
    BACKGROUND_PROCESSING = 1
    BACKGROUND_PASSED = 2
    BACKGROUND_FAILED = 3

    BACKGROUND_CHOICES = (
        (BACKGROUND_NOT_STARTED, 'Not Started'),
        (BACKGROUND_PROCESSING, 'Processing'),
        (BACKGROUND_PASSED, 'Passed'),
        (BACKGROUND_FAILED, 'Failed'),
    )

    flight_reservation = models.ForeignKey('reservations.FlightReservation')
    userprofile = models.ForeignKey('accounts.UserProfile', on_delete=models.SET_NULL,null=True)
    user = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True)
    companion = models.BooleanField(default=False)
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    email = models.EmailField(null=True)
    phone = PhoneNumberField(blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    checked_in = models.BooleanField(default=False)
    background_status = models.PositiveIntegerField(choices=BACKGROUND_CHOICES, default=BACKGROUND_NOT_STARTED)

    def get_full_name(self):
        return u'%s %s' % (self.first_name, self.last_name)

    def check_in(self):
        """
        Checks in the passenger
        """
        self.checked_in = True
        self.save()
        self.flight_reservation.check_in()

    def fake_user(self):
        """
        Creates a fake user object with the passenger details
        """
        User = get_user_model()
        return User(first_name=self.first_name, last_name=self.last_name, email=self.email)

    def fake_userprofile(self):
        """
        Creates a fake user object with the passenger details
        """
        from accounts.models import UserProfile
        return UserProfile(first_name=self.first_name, last_name=self.last_name, email=self.email)

    def handle_noshow(self, admin_user=None):
        """
        Used when a person has not checked in by the time the flight completes.
        Creates a no-show record and if they have three no-shows,
        creates a NoShowRestriction starting immediately
        Returns:

        """

        from pytz import timezone
        with transaction.atomic():
            from accounts.models import UserNoShow
            noshow = UserNoShow()
            # noshow.user = self.user # this will eventually go away.
            # from accounts.models import UserProfile
            # profile = UserProfile.objects.filter(user_id=self.user.id)
            noshow.userprofile = self.userprofile
            noshow.flight = self.flight_reservation.flight
            noshow.save()

            # we only count no-shows within certain time period
            penaltycheckdate = datetime.now() - relativedelta(days=settings.NO_SHOW_PENALTY_ASSESSMENT_DAYS)
            count = UserNoShow.objects.filter(userprofile_id=self.userprofile.id, created__gte=penaltycheckdate).count()
            if count >= 3:
                # create restriction window!
                from accounts.models import UserNoShowRestrictionWindow
                restriction = UserNoShowRestrictionWindow()
                # restriction.user = self.user
                restriction.userprofile = self.userprofile
                restriction.start_date = datetime.now(pytz.utc)

                restriction.end_date = restriction.start_date  + relativedelta(days=settings.NO_SHOW_PENALTY_DAYS)
                restriction.save()

                # any reservations for this passenger on regularly scheduled flights in the restriction window need to be cancelled
                # NOT including the current one triggering this as that will be set to no-show
                statuses_in = ['R','P']
                reservations = FlightReservation.objects.filter(flight__flight_type='R', reservation__account=self.userprofile.account, flight__departure__gte=restriction.start_date, flight__departure__lte=restriction.end_date, status__in=statuses_in).exclude(flight=self.flight_reservation.flight).all()
                for res in reservations:
                    # see if this member is a passenger
                    passenger_record = res.passenger_set.filter(userprofile=self.userprofile).first()
                    if passenger_record:
                        passcount = res.passenger_count
                        removal = FlightPassengerAuditTrail()
                        removal.flight_id = res.flight_id
                        removal.passenger_id = passenger_record.id
                        removal.user_profile = self.userprofile
                        removal.passenger_first_name = self.first_name
                        removal.passenger_last_name = self.last_name
                        removal.update_type = FlightPassengerAuditTrail.UPDATE_PASSENGER_REMOVED
                        removal.update_details = "Passenger removed from flight due to excessive no-shows."
                        removal.passenger_date_of_birth = self.date_of_birth
                        removal.created = datetime.now()
                        if admin_user:
                            removal.created_by = admin_user
                        removal.save()
                        passenger_record.delete()
                        if passcount == 1:
                            # cancel the reservation
                            res.cancellation_reason = "Passenger restricted due to excessive no-shows."
                            res.cancel(user=admin_user, refund_eligible=False, flight_cancelled=False)
                            # the parent reservation needs cancellation as well (this was just flight reservation.
                            parent = res.reservation
                            parent.cancel(False)

                # any wishlists during the restriction period need to be removed.
                wishlists = FlightWaitlist.objects.filter(userprofile_id = self.userprofile.id, status=FlightWaitlist.STATUS_WAITING).all()
                for wishlist in wishlists:
                    if wishlist.flight.departure >= restriction.start_date and wishlist.flight.departure <= restriction.end_date:
                        wishlist.cancel()

    def __unicode__(self):
        return 'Passenger %s %s' % (self.first_name, self.last_name)


class FlightWaitlist(models.Model):
    """
    A waitlist for a particular flight

    user: The user waiting on this flight
    flight: The flight the user is waiting on
    passenger_count: how many passengers associated with this waitlist
    created: When the user expressed interesting in waiting for this flight
    """

    STATUS_WAITING = 'W'
    STATUS_RESERVED = 'R'
    STATUS_CANCELLED = 'C'
    STATUS_EXPIRED = 'E'

    STATUS_CHOICES = (
        (STATUS_WAITING, 'Waiting'),
        (STATUS_RESERVED, 'Reserved'),
        (STATUS_CANCELLED, 'Cancelled'),
        (STATUS_EXPIRED, 'Expired')
    )

    user = models.ForeignKey('accounts.User', null=True)
    userprofile = models.ForeignKey('accounts.UserProfile', null=True)
    flight = models.ForeignKey('flights.Flight')
    passenger_count = models.PositiveIntegerField(default=0)
    created = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=1, choices=STATUS_CHOICES, default=STATUS_WAITING)

    class Meta:
        unique_together = ('userprofile', 'flight')

    def send_waitlist_email(self):
        """
        Send's the added to waitlist email to the user.
        """
        context = {
            'flight_waitlist': self,
            'flight': self.flight,
            'member': self.userprofile,
        }

        subject = 'You\'ve been added to the wishlist'

        to_emails = [self.userprofile.email]
        if to_emails:
            send_html_email_task.delay('emails/added_waitlist', context, subject, settings.DEFAULT_FROM_EMAIL, to_emails,)

        subject_notify = 'Addition to the wishlist for %s' % self.flight
        send_html_email_task.delay('emails/added_waitlist_notify', context, subject_notify, settings.DEFAULT_FROM_EMAIL, settings.WAITLIST_NOTIFICATION_LIST)

    def cancel(self):
        self.status = self.STATUS_CANCELLED
        self.save()

    def expire(self):
        self.status = self.STATUS_EXPIRED
        self.save()

    def __unicode__(self):
        return 'FlightWaitlist for %s on %s' % (self.userprofile.get_full_name(), self.flight)


class FlightPassengerAuditTrail(models.Model):
    """
    Tracks updates to passengers for a flight

    flight: the flight connected with the update
    passener: the passenger for this update
    passenger_first_name: The passenger's first name
    passenger_last_name: The passenger's last name
    passenger_date_of_birth: The passenger's date of birth for background check
    update_type: the type of update made
    udpate_details: the details
    created_by: the user that created this audit
    """

    UPDATE_BACKGROUND_CHECK_STATUS = 0
    UPDATE_PASSENGER_REMOVED = 1

    UPDATE_CHOICES = (
        (UPDATE_BACKGROUND_CHECK_STATUS, 'Update Background Check Status'),
        (UPDATE_PASSENGER_REMOVED, 'Passenger removed from flight')
    )

    flight = models.ForeignKey('flights.Flight', on_delete=models.SET_NULL, null=True, blank=True)
    passenger = models.ForeignKey('Passenger', on_delete=models.SET_NULL, null=True, blank=True)
    user_profile = models.ForeignKey('accounts.UserProfile', on_delete=models.SET_NULL, null=True, blank=True)
    passenger_first_name = models.CharField(max_length=30)
    passenger_last_name = models.CharField(max_length=30)
    passenger_date_of_birth = models.DateField()
    update_type = models.PositiveIntegerField(choices=UPDATE_CHOICES, default=UPDATE_BACKGROUND_CHECK_STATUS)
    update_details = models.TextField(max_length=160)
    created = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True)

    def __unicode__(self):
        return '(%s) Update for Flight %s: %s' % (self.passenger, self.flight.flight_number, self.update_details)
