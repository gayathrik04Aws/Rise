from __future__ import division

from collections import defaultdict

from auditlog.registry import auditlog
from decimal import Decimal

from django.db import models, transaction
from django.conf import settings
from django.db.models.query_utils import Q
from django.db.models import F

from billing.models import GenericBillingException, BankAccount
from flights.models import BaseRoute, Flight, FlightReservation, Reservation
import flights.const as flights_const

from htmlmailer.mailer import send_html_email
from core.tasks import send_html_email_task

import uuid, datetime

from reservations.models import ReservationError, Passenger
from mixins import AnywherePricingMixin


class AnywhereRoute(BaseRoute):
    """
    A potential route for Rise Anywhere.
    """
    cost = models.DecimalField('full flight cost', max_digits=20, decimal_places=2)

    def __unicode__(self):
        return 'Anywhere Route %s -> %s in %s' % (self.origin.code, self.destination.code, self.duration)


class AnywhereFlightRequest(models.Model, AnywherePricingMixin):
    """
    A pending request for a Rise Anywhere flight.
    """
    WHEN_MORNING = 'morning'
    WHEN_AFTERNOON = 'afternoon'
    WHEN_EVENING = 'evening'
    WHEN_FLEXIBLE = 'anytime'

    WHEN_CHOICES = (
        (WHEN_MORNING, 'Morning'),
        (WHEN_AFTERNOON, 'Afternoon'),
        (WHEN_EVENING, 'Evening'),
        (WHEN_FLEXIBLE, 'Anytime')
    )

    STATUS_NEW = 'new'  #: being created (or abandoned - probably want to clean up stale 'new' records regularly)
    STATUS_PENDING = 'pending'  #: awaiting a Rise agent's decision
    STATUS_ACCEPTED = 'accepted'  #: accepted by a Rise agent
    STATUS_REJECTED = 'rejected'  #: rejected by a Rise agent

    STATUS_CHOICES = (
        (STATUS_NEW, 'New'),
        (STATUS_PENDING, 'Pending'),
        (STATUS_ACCEPTED, 'Accepted'),
        (STATUS_REJECTED, 'Rejected')
    )

    MAX_SEATS = 8  # placeholder until seat logic exists

    status = models.CharField('Request Status', max_length=64, default=STATUS_NEW, choices=STATUS_CHOICES)
    created = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey('accounts.User', null=True, on_delete=models.SET_NULL,
                                   related_name='anywhere_flight_requests')
    origin_city = models.ForeignKey('flights.Airport', null=True, on_delete=models.SET_NULL, related_name='+')
    destination_city = models.ForeignKey('flights.Airport', null=True, on_delete=models.SET_NULL, related_name='+')

    is_round_trip = models.BooleanField('Flight is Round-Trip?', default=False)
    depart_date = models.DateField('Departure Date', null=True,blank=True)
    depart_when = models.CharField('Depart Time', choices=WHEN_CHOICES, max_length=64, default=WHEN_FLEXIBLE)

    return_date = models.DateField('Returning Date', null=True, blank=True)
    return_when = models.CharField('Return Time', choices=WHEN_CHOICES, max_length=64, default=WHEN_FLEXIBLE,
                                   null=True, blank=True)

    seats = models.IntegerField('# Seats Requested', null=False)
    sharing = models.CharField('Share Flight With', max_length=64, choices=flights_const.SHARING_CHOICES,
                               default=flights_const.SHARING_OPTION_PUBLIC)

    outbound_route = models.ForeignKey('AnywhereRoute', null=True, related_name='request_outbound_route')
    return_route = models.ForeignKey('AnywhereRoute', null=True, related_name='request_return_route')

    seats_required = models.IntegerField('# Seats Booked To Confirm', null=False, default=6)

    @property
    def depart_date_display(self):
        return self.depart_date.strftime('%b %d, %Y')

    @property
    def return_date_display(self):
        if self.return_date is not None:
            return self.return_date.strftime('%b %d, %Y')
        return ""

    @property
    def date_crumb(self):
        if self.return_date is not None:
            return "%s -> %s" % (self.depart_date_display, self.return_date_display)
        return self.depart_date_display
    # routes need to be optional because eventually people will be able to go from anywhere to anywhere
    # we just will only show average price if we have that info.
    def set_routes(self):
        if self.origin_city is None or self.destination_city is None:
            return None
        self.outbound_route = AnywhereRoute.objects.filter(origin_id=self.origin_city_id,
                                                           destination_id=self.destination_city_id).first()
        if self.is_round_trip:
            self.return_route = AnywhereRoute.objects.filter(origin_id=self.destination_city_id,
                                                             destination_id=self.origin_city_id).first()
        return None

    @property
    def full_flight_cost(self):
        # exists just so the Mixin can use consistent property name.
        return Decimal(self.estimated_cost)

    @property
    def estimated_cost(self):
        # moved logic into mixin
        return self.estimate_total_flight_cost(self.is_round_trip, self.outbound_route, self.return_route, self.depart_date, self.return_date)

    def get_estimated_cost_for_leg(self,step):
        # move logic to mixin
        return self.estimate_leg_cost(int(step) + 1, self.is_round_trip, self.outbound_route, self.return_route, self.depart_date, self.return_date)


    @property
    def duration(self):
        """
        Return a placeholder duration between 30 minutes and 4 hours
        """
        # TODO: MVP: Fix this pseudorandom placeholder.
        return (hash(str(self.pk)) % 210) + 30

    @property
    def cost_per_seat(self):
        """
        Changed per seat calculation to be based on # of seats required to book
        Returns:

        """
        return Decimal(self.estimated_cost)/ self.seats_required

    @property
    def empty_seats(self):
        """
        The number of seats not being reserved by the Requester
        """
        return self.total_seats - self.seats

    @property
    def total_seats(self):
        return self.MAX_SEATS

    @property
    def min_cost(self):
        """
        The estimated minimum the creator would have to pay if every other non-Companion seat is booked by a stranger.
        """

        return self.estimated_cost - (self.cost_per_seat * self.empty_seats)

    @property
    def percent_full(self):
        """
        Return pre-multiplied percentage of flight filled-ness.
        """
        if self.seats >= self.total_seats:
            return 100
        return int(self.seats * 100 / self.total_seats)

    @property
    def route_description(self):
        if self.is_round_trip:
            return u'{} <=> {}'.format(self.origin_city, self.destination_city)
        else:
            return u'{} ==> {}'.format(self.origin_city, self.destination_city)

    def __unicode__(self):
        return u'Anywhere Flight Request %s [%s]' % (self.id, self.route_description)

    @property
    def trip_type_display(self):
        if self.is_round_trip:
            return 'Round Trip'

        return 'One Way'

    @property
    def email_context(self):
        return {
            'origin': self.origin_city,
            'destination': self.destination_city,
            'depart_date': self.depart_date,
            'depart_when': self.depart_when,
            'return_date': self.return_date,
            'return_when': self.return_when,
            'is_roundtrip': self.is_round_trip,
            'creator_name': self.created_by.get_full_name(),
            'passengers': self.seats - 1,
            'sharing': self.sharing,
            'estimated_cost': self.estimated_cost,
            'seats_required' : self.seats_required,
            'cost_per_seat':self.cost_per_seat,
            'total_seats' : self.total_seats
        }

    @property
    def days_to_departure(self):
        now = datetime.datetime.now()
        delta = self.depart_date - now.date()
        return delta.days

    def send_request_received_email(self):
        to = [self.created_by.email]
        title = "Rise Anywhere Flight Request Received"
        subject = "Rise Anywhere Flight Request Received"
        context = self.email_context

        context.update({
            'title': title,
            'your_estimated_total': self.seats * self.cost_per_seat
        })
        send_html_email_task.delay('emails/anywhere_request_received', context, subject, settings.DEFAULT_FROM_EMAIL,
                                   to)

        send_html_email_task.delay('emails/anywhere_request_received_internal', context, subject, settings.DEFAULT_FROM_EMAIL,
                                   settings.ANYWHERE_FLIGHT_REQUEST_NOTIFICATION)

    def decline(self):
        assert self.status == AnywhereFlightRequest.STATUS_PENDING, 'Can only decline PENDING requests'
        self.status = AnywhereFlightRequest.STATUS_REJECTED
        self.save()

        to = [self.created_by.email]
        title = "Rise Anywhere Flight Request Declined"
        subject = "Rise Anywhere Flight Request Declined"
        context = self.email_context
        context.update({
            'title': title
        })
        send_html_email_task.delay('emails/anywhere_request_declined', context, subject, settings.DEFAULT_FROM_EMAIL,
                                   to)


class AnywhereFlightSet(models.Model, AnywherePricingMixin):
    """
    Represents the one or two legs in an Anywhere Flight set, since they are not sold separately.
    Is used as the ViewModel for Anywhere Flight Details
    """

    CONFIRMATION_STATUS_NOTREADY = 'NOTFULL'
    CONFIRMATION_STATUS_FULLPENDING = 'PENDINGCONFIRMATION'
    CONFIRMATION_STATUS_CONFIRMED = 'CONFIRMED'
    CONFIRMATION_STATUS_CANCELLED = 'CANCELLED'
    CONFIRMATION_STATUS_PARTLYCANCELLED = 'PARTLYCANCELLED'

    CONFIRMATION_STATUS_CHOICES = (
        (CONFIRMATION_STATUS_NOTREADY, 'Not Ready'),
        (CONFIRMATION_STATUS_FULLPENDING, 'Full - Pending Confirmation'),
        (CONFIRMATION_STATUS_CONFIRMED, 'Confirmed'),
        (CONFIRMATION_STATUS_CANCELLED, 'Cancelled'),
        (CONFIRMATION_STATUS_PARTLYCANCELLED, 'Leg 1 Complete / Leg 2 Cancelled')
    )

    public_key = models.UUIDField(default=uuid.uuid4, editable=False, null=False, unique=True, db_index=True)

    leg1 = models.ForeignKey('flights.Flight', null=False, related_name="OUTBOUND")
    leg2 = models.ForeignKey('flights.Flight', null=True, on_delete=models.SET_NULL, related_name="RETURN")
    full_flight_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    per_seat_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    anywhere_request = models.ForeignKey('anywhere.AnywhereFlightRequest', null=False)
    flight_creator_user = models.ForeignKey('accounts.User', null=False, related_name="flight_creator")
    confirmation_status = models.CharField(max_length=20, choices=CONFIRMATION_STATUS_CHOICES,
                                           default=CONFIRMATION_STATUS_NOTREADY)
    sharing = models.CharField(max_length=12, choices=flights_const.SHARING_CHOICES,
                               default=flights_const.SHARING_OPTION_PUBLIC)
    created_by = models.ForeignKey('accounts.User', null=True, on_delete=models.SET_NULL, blank=True,
                                   related_name="set_created_by")
    seats_required = models.IntegerField('# Seats booked to confirm', default=6, null=False)

    @property
    def outbound_route(self):
        if not self.anywhere_request:
            return None
        return self.anywhere_request.outbound_route

    @property
    def return_route(self):
        if not self.anywhere_request:
            return None
        return self.anywhere_request.return_route

    @property
    def days_to_departure(self):
        now = datetime.datetime.now()
        delta = self.leg1.departure.date() - now.date()
        return delta.days

    @property
    def per_seat_tax(self):
        return self.per_seat_cost * settings.FET_TAX

    @property
    def per_seat_with_tax(self):
        return self.per_seat_cost + self.per_seat_tax

    @property
    def is_oneway(self):
        return self.leg2 is None

    @property
    def is_round_trip(self):  # to match AnywhereFlightRequest
        return not self.is_oneway

    @property
    def empty_seats(self):
        if self.leg1 is None:
            return -1
        return self.leg1.seats_available

    @property
    def total_seats(self):
        if self.leg1 is None:
            return -1
        return self.leg1.seats_total

    @property
    def origin(self):
        if self.leg1 is None:
            return ""
        return self.leg1.origin

    @property
    def destination(self):
        if self.leg1 is None:
            return ""
        return self.leg1.destination

    @property
    def depart_date(self):
        if self.leg1 is None:
            return None
        return self.leg1.local_departure

    @property
    def return_date(self):
        if self.leg2 is None:
            return None
        return self.leg2.local_departure

    @property
    def percent_full(self):
        if self.leg1 is None:
            return 0
        taken_seats = self.total_seats - self.empty_seats
        if taken_seats > self.total_seats:
            return 100
        fraction = taken_seats / self.total_seats
        percentage = int(fraction * 100)
        return percentage

    @property
    def passenger_query(self):
        """
        Return a query object that queries all Passengers connected to this FlightSet.
        """
        f = Q(flight_reservation__flight=self.leg1)

        if self.leg2:
            f |= Q(flight_reservation__flight=self.leg2)

        return Passenger.objects.filter(f)

    @staticmethod
    def get_anywhere_ready_queryset():
        subset = AnywhereFlightSet.objects.filter(Q(leg1__departure__gte=datetime.datetime.now)).values_list('id', flat=True)
        return AnywhereFlightSet.objects.filter(
            confirmation_status=AnywhereFlightSet.CONFIRMATION_STATUS_FULLPENDING,id__in=subset).order_by('leg1__departure')

    @staticmethod
    def get_anywhere_unconfirmed_queryset():
        subset = AnywhereFlightSet.objects.filter(Q(leg1__departure__gte=datetime.datetime.now)).values_list('id', flat=True)
        return AnywhereFlightSet.objects.filter(
            confirmation_status=AnywhereFlightSet.CONFIRMATION_STATUS_NOTREADY,id__in=subset).order_by('leg1__departure')

    @staticmethod
    def get_anywhere_confirmed_queryset():
        subset = AnywhereFlightSet.objects.filter(Q(leg1__departure__gte=datetime.datetime.now) or Q(leg2__departure__gte=datetime.datetime.now)).exclude(Q(leg1__status='C')).values_list('id', flat=True)
        return AnywhereFlightSet.objects.filter(
            confirmation_status=AnywhereFlightSet.CONFIRMATION_STATUS_CONFIRMED,id__in=subset).order_by('leg1__departure')


    @staticmethod
    def get_available_flightsets():
        return AnywhereFlightSet.objects.filter(Q(leg1__seats_available__gt=0) & Q(sharing=flights_const.SHARING_OPTION_PUBLIC)
                                                & Q(leg1__departure__gte=datetime.datetime.now)).exclude(confirmation_status='CANCELLED').order_by('leg1__departure').all()


    def create(self, flight_request, leg1, leg2=None, created_by=None):
        """
        Creates an AnywhereFlightSet from one or two flights, a flight request and the current user
        Args:
            leg1: outbound Flight
            leg2: return Flight (optional)
            flight_request: AnywhereFlightRequest
            created_by: User

        Returns:

        """
        self.leg1 = leg1
        self.leg2 = leg2
        if leg2 is None:
            self.full_flight_cost = leg1.anywhere_details.full_flight_cost
            self.per_seat_cost = leg1.anywhere_details.per_seat_cost
        else:
            self.full_flight_cost = leg1.anywhere_details.full_flight_cost + leg2.anywhere_details.full_flight_cost
            self.per_seat_cost = leg1.anywhere_details.per_seat_cost + leg2.anywhere_details.per_seat_cost
        self.confirmation_status = self.CONFIRMATION_STATUS_NOTREADY
        self.sharing = flight_request.sharing
        self.anywhere_request = flight_request
        self.flight_creator_user = flight_request.created_by
        self.created_by = created_by

        # Ensure that seats_required does not exceed plane seat capacity.
        if self.leg2 is not None and self.leg2.plane.seats < self.leg1.plane.seats:
            plane_seats = self.leg2.plane.seats
        else:
            plane_seats = self.leg1.plane.seats

        if plane_seats < flight_request.seats_required:
            self.seats_required = plane_seats
        else:
            self.seats_required = flight_request.seats_required

        self.save()

    def reserve_creator_seats(self, created_by):
        """
        Books the number of seats requested by the flight creator for the creator based
        on their initial flight request.
        Args:
            created_by: user making the reservation

        Returns:

        """
        seats = self.anywhere_request.seats
        if self.sharing == flights_const.SHARING_OPTION_PRIVATE:
            seats = -1  # if seats set to -1 this will indicate to book all seats on plane based on # of seats
        return self.reserve_seats(self.anywhere_request.created_by.userprofile, seats, created_by, True)

    def reserve_seats(self, userprofile, seats, created_by, for_creator=False):
        """
        Books the requested number of seats on behalf of a user.
        Note that initially this will only ever be 1 for everyone but flight creator

        Args:
            user:
            created_by:

        Returns:

        """
        if seats == -1:
            leg1cost = self.total_seats * self.leg1.anywhere_details.per_seat_cost
        else:
            leg1cost = seats * self.leg1.anywhere_details.per_seat_cost
        leg1_reservation = self.leg1.reserve_anywhere_flight(created_by, userprofile,
                                                             seats, leg1cost)

        if not leg1_reservation:
            return None

        if self.leg2 is not None:
            if seats == -1:
                leg2cost = self.total_seats * self.leg2.anywhere_details.per_seat_cost
            else:
                leg2cost = seats * self.leg2.anywhere_details.per_seat_cost
            leg2_reservation = self.leg2.reserve_anywhere_flight(created_by, userprofile,
                                                                 seats, leg2cost, leg1_reservation.reservation)

        self.leg1.refresh_from_db()
        num_seats = self.leg1.seats_available
        if num_seats > 0:
            # we have to recalculate price
            self.recalculate_seat_costs(num_seats)



        # if all seats are now booked we need to change the status of the flightset
        # since you have to book both legs if either flight is full, then the set is full
        # need to retrieve Flight fresh because this instance may not be updated.

        if self.has_met_seat_requirement() and self.confirmation_status == self.CONFIRMATION_STATUS_NOTREADY:
            self.confirmation_status = self.CONFIRMATION_STATUS_FULLPENDING
            self.save()

        if for_creator:
            self.send_request_approved_email()
        else:
            leg1_reservation.reservation.send_anywhere_reservation_email()
        return leg1_reservation.reservation

    def has_met_seat_requirement(self):
        if self.total_seats - self.leg1.seats_available >= self.seats_required:
            return True
        return False

    def update_final_costs(self):
        """
        Updates the final costs on the flight reservations for this flightset & calculates refunds due

        Returns:

        """
        flightres_list = FlightReservation.objects.filter(Q(flight_id=self.leg1_id)).all()
        # RISE 157 - AMF get per_seat_cost based on number of seats booked, not on the current per_seat_cost, because that per seat cost is
        # what the NEXT seat would be charged!
        leg_full_cost = self.leg1.anywhere_details.full_flight_cost
        per_seat_cost = self.leg_per_seat_price(leg_full_cost, self.leg1.seats_total-self.leg1.seats_available)
        for flightres in flightres_list:
            flightres.final_adjusted_seat_cost = per_seat_cost * flightres.passenger_count
            flightres.final_adjusted_tax = (flightres.final_adjusted_seat_cost + flightres.other_charges) * settings.FET_TAX
            adjusted_total = flightres.final_adjusted_seat_cost + flightres.final_adjusted_tax + flightres.other_charges
            if flightres.anywhere_total_cost > adjusted_total:
                flightres.anywhere_refund_due = flightres.anywhere_total_cost - adjusted_total
            flightres.save()

        if self.leg2:
            flightres_list = FlightReservation.objects.filter(flight_id=self.leg2_id).all()
            # RISE 157 - AMF get per_seat_cost based on number of seats booked, not on the current per_seat_cost, because that per seat cost is
            # what the NEXT seat would be charged!
            leg_full_cost = self.leg2.anywhere_details.full_flight_cost
            per_seat_cost = self.leg_per_seat_price(leg_full_cost, self.leg2.seats_total-self.leg2.seats_available)
            for flightres in flightres_list:
                flightres.final_adjusted_seat_cost = per_seat_cost * flightres.passenger_count
                flightres.final_adjusted_tax = (flightres.final_adjusted_seat_cost + flightres.other_charges) * settings.FET_TAX
                adjusted_total = flightres.final_adjusted_seat_cost + flightres.final_adjusted_tax + flightres.other_charges
                if flightres.anywhere_total_cost > adjusted_total:
                    flightres.anywhere_refund_due = flightres.anywhere_total_cost - adjusted_total
                flightres.save()

    def update_costs_at_confirmation(self):
        """
        Updates the cost, tax fields based on price at the time of confirmation (when the charge is made).
        Because confirmation can run multiple times only update reservations still pending.
        Returns:

        """
        seats_booked = self.total_seats - self.leg1.seats_available
        flightres_list = FlightReservation.objects.filter(Q(flight_id=self.leg1_id) & Q(status=FlightReservation.STATUS_ANYWHERE_PENDING)).all()
        for flightres in flightres_list:
            basefare = flightres.flight.anywhere_details.full_flight_cost / seats_booked
            flightres.cost = basefare * flightres.passenger_count
            flightres.tax = (flightres.cost + flightres.other_charges) * settings.FET_TAX
            flightres.save()

        if self.leg2:
            flightres_list = FlightReservation.objects.filter(Q(flight_id=self.leg2_id) & Q(status=FlightReservation.STATUS_ANYWHERE_PENDING)).all()
            for flightres in flightres_list:
                basefare = flightres.flight.anywhere_details.full_flight_cost / seats_booked
                flightres.cost = basefare * flightres.passenger_count
                flightres.tax = (flightres.cost + flightres.other_charges) * settings.FET_TAX
                flightres.save()

    def recalculate_seat_costs(self, available_seats):
        """
        As seats are booked have to see how many seats are available and update cost if that number
        exceeds the seats_required.

        """
        seats_booked = self.total_seats - available_seats
        if seats_booked >= self.seats_required:
            next_seat = seats_booked+1
        else:
            next_seat = self.seats_required
        with transaction.atomic():
            self.per_seat_cost = self.full_flight_cost / next_seat
            self.leg1.anywhere_details.per_seat_cost = self.leg1.anywhere_details.full_flight_cost / next_seat
            if self.leg2 and self.leg2.anywhere_details:
                self.leg2.anywhere_details.per_seat_cost = self.leg2.anywhere_details.full_flight_cost / next_seat
                self.leg2.anywhere_details.save()
                self.leg2.anywhere_details.refresh_from_db()
            self.save()
            self.leg1.anywhere_details.save()
            self.leg1.anywhere_details.refresh_from_db()
            self.refresh_from_db()

    def send_refund_error_mail(self):
        # TODO: Remove the return below and test this.
        title = "Rise Anywhere Flight Refund Error"
        subject = "Rise Anywhere Flight Refund Error"

        to = settings.ANYWHERE_REFUND_ERROR_NOTIFICATION_LIST
        context = {
            'title': title,
            'flightset': self
        }
        for mailto in to:
            send_html_email_task.delay('emails/admin_anywhere_autorefund_failed', context, subject, settings.DEFAULT_FROM_EMAIL,
                                   [mailto])

    def send_overage_refund_email(self, reservation, payment_method):
        # TODO: Remove the return below and test this.
        title = "Rise Anywhere Reservation Refund Processed"
        subject = "Rise Anywhere Reservation Refund Processed"

        if isinstance(payment_method, BankAccount):
            payment_method_type = "bank account"
        else:
            payment_method_type = "credit card"

        context = {
            'leg1': self.leg1,
            'leg2': self.leg2,
            'public_key': self.public_key,
            'title': title,
            'previous_charge': reservation.charge.amount,
            'amount_refunded': reservation.charge.amount_refunded,
            'seat_cost': reservation.calculate_final_adjusted_seat_cost(),
            'other_charges': reservation.calculate_anywhere_other_charges(),
            'other_desc': self.get_other_charge_description(),
            'tax': reservation.calculate_final_adjusted_tax(),
            'your_total': reservation.calculate_final_adjusted_total(),
            'method_of_payment': payment_method_type
        }
        if reservation.account == self.anywhere_request.created_by.account:
            context['seats'] = self.anywhere_request.seats
        else:
            context['seats'] = 1

        #Only email the primary for each reservation, not all passengers.
        flight_reservation = FlightReservation.objects.filter(reservation_id=reservation.id, reservation__account_id=reservation.account_id).first()
        passengers = Passenger.objects.filter(flight_reservation_id=flight_reservation.id).all()
        for passenger in passengers:
            to = [passenger.userprofile.email]
            #Flight creator may have passengers on his reservation that don't get the pricing details because the flight creator paid.
            #Two different templates for passengers NOT belonging to the reservation's account & for the person whose reservation it is.
            if passenger.userprofile.account_id == reservation.account_id:
                context['passengers'] = passengers
                send_html_email_task.delay('emails/anywhere_refund_processed', context, subject, settings.DEFAULT_FROM_EMAIL,
                                   to)

    def process_overpaid_passenger_refunds(self,created_by):
        """
        Any reservation that has paid more than the current seat cost gets a refund, if they haven't already got one.
        Returns:

        """
        legs = [self.leg1]
        if self.leg2 is not None:
            legs.append(self.leg2)

        statuslist = ['A','P']
        reservations = set()
        for leg in legs:
            reservations.update(fr.reservation for fr in
                                leg.flightreservation_set.filter(Q(anywhere_refund_due__gt=0) & Q(anywhere_refund_paid=False)).exclude(status__in=statuslist))

        # could regroup by account here, but things should be clean enough already to iterate through the Reservations

        # pre-process reservations, checking for errors before performing any permanent actions
        reservations_to_process = []
        reservations_failed = []

        for r in reservations: #reservation not flightreservation
            assert r.charge is not None, 'Reservation was never charged'
            card = r.charge.card
            bankaccount = r.charge.bank_account
            if card is not None:
                payment_method = card
            else:
                payment_method = bankaccount

            if payment_method is None:
                reservations_failed.append((r.pk, '{} has no valid payment methods'.format(r.account)))
                continue

            if isinstance(payment_method, BankAccount):
                if not payment_method.verified:
                    reservations_failed.append((r.pk, "{}'s Bank Account is unverified".format(r.account)))
                    continue


            reservations_to_process.append((
                r, payment_method
            ))

        # we could check for pre-processing errors here and bubble them up, but for MVP we're going to just keep going
        # and show them at the end.

        for reservation, payment_method in reservations_to_process:

            with transaction.atomic():
                try:
                    refund_due = reservation.calculate_anywhere_refund()
                    reservation.charge.refund(refund_due, 'RISE Anywhere Flight Reservation {reservation.pk} / Flight # {reservation.flight_numbers} overestimated fare refund'.format(reservation=reservation), created_by)

                except GenericBillingException as E:
                    # we've already started processing cards, so delay failures til the end
                    # we could also refund all charges, or rewrite billing to authorize and charge in two passes...
                    reservations_failed.append((reservation, 'Refund {} failed: {}'.format(payment_method, E.message)))
                    continue

                for flightres in reservation.flightreservation_set.filter(Q(anywhere_refund_due__gt=0) & Q(anywhere_refund_paid=False)).exclude(Q(status=FlightReservation.STATUS_CANCELLED)).all():
                    flightres.anywhere_refund_paid = True
                    flightres.save()
                reservation.save()  # explicitly save despite reserve() also saving.

            # Not sending email inside the transaction because we don't want to reverse the transaction over failed email
            # todo:  method not yet implemented
            self.send_overage_refund_email(reservation, payment_method)

        if reservations_failed:
            # Sentry will contain the locals() for this
            # TODO MVP : descriptive error for Rise agents

            # raising this error is already sort of descriptive
            # note that if the refunds are triggered by the flight filling, we don't want to show this message to the
            # user because the user is the person who booked the last seat.  So catching method will need to send email
            # to notify RISE that the refunds didn't all process.
            self.send_refund_error_mail()
            raise ReservationError(
                'Failed to refund all overcharged Reservations',
                reservations_failed=reservations_failed
            )

    def send_request_approved_email(self):
        to = [self.flight_creator_user.email]
        title = "Rise Anywhere Flight Request Approved"
        subject = "Rise Anywhere Flight Request Approved"
        if self.sharing == flights_const.SHARING_OPTION_PRIVATE:
            your_cost = self.per_seat_cost * self.total_seats
        else:
            your_cost = self.per_seat_cost * self.anywhere_request.seats
        your_tax = your_cost * settings.FET_TAX
        your_total = your_cost + your_tax
        context = {
            'leg1': self.leg1,
            'leg2': self.leg2,
            'seats': self.anywhere_request.seats,
            'total_cost': self.full_flight_cost,
            'your_cost': your_cost,
            'your_tax': your_tax,
            'your_total': your_total,
            'public_key': self.public_key,
            'title': title,
            'seats_required':self.anywhere_request.seats_required,
            'cost_per_seat':self.anywhere_request.cost_per_seat,
            'total_seats': self.anywhere_request.total_seats
        }
        send_html_email_task.delay('emails/anywhere_request_approved', context, subject, settings.DEFAULT_FROM_EMAIL,
                                   to)

    def send_email_invitations(self, invitees):
        """
        Takes a semi-colon delimited list of email addresses and sends the invitation email to them.
        Args:
            invitees: semi-colon delimited list of email addresses

        Returns:

        """
        invite_list = invitees.split(";")

        creator_name = self.anywhere_request.created_by.get_full_name()

        subject = settings.ANYWHERE_INVITATION_SUBJECT.replace('<creator>', creator_name)
        title = "You're invited!"

        total_cost = self.leg1.anywhere_details.per_seat_cost
        if self.leg2 is not None:
            total_cost = total_cost + self.leg2.anywhere_details.per_seat_cost

        context = {
            'leg1': self.leg1,
            'leg2': self.leg2,
            'creator_name': creator_name,
            'seats': 1,
            'total_cost': total_cost,
            'public_key': self.public_key,
            'title': title
        }
        # when I send all the email addresses at once, the SMTP connection unexpectedly closes.
        # for MVP debugging email sender is way out of scope.
        # so sending one at a time
        for email in invite_list:
            email_as_list = [email]
            send_html_email_task.delay('emails/anywhere_invite', context, subject, settings.DEFAULT_FROM_EMAIL,
                                       email_as_list)

    def complete_reservations(self, confirmed_by):
        """
        Attempt to charge any outstanding Reservations.

        Raises an error
        """
        # have to jump from FlightSet to Flight to FlightReservation to Reservation to actually complete the reservations...

        # collect `Reservation`s from legs->flightreservation_set->reservation


        #Make sure all pending reservations are going to be charged at the current per-seat cost.
        self.update_costs_at_confirmation()

        legs = [self.leg1]
        if self.leg2 is not None:
            legs.append(self.leg2)

        reservations = set()
        for leg in legs:
            reservations.update(fr.reservation for fr in
                                leg.flightreservation_set.filter(status=FlightReservation.STATUS_ANYWHERE_PENDING))

        # could regroup by account here, but things should be clean enough already to iterate through the Reservations

        # pre-process reservations, checking for errors before performing any permanent actions
        reservations_to_process = []
        reservations_failed = []

        for r in reservations:
            assert r.charge is None, 'PENDING Reservation already has charge'
            payment_method = r.account.get_default_payment()

            if payment_method is None:
                reservations_failed.append((r.pk, '{} has no valid payment methods'.format(r.account)))
                continue

            if isinstance(payment_method, BankAccount):
                if not payment_method.verified:
                    reservations_failed.append((r.pk, "{}'s Bank Account is unverified".format(r.account)))
                    continue

            reservations_to_process.append((
                r, payment_method
            ))

        # we could check for pre-processing errors here and bubble them up, but for MVP we're going to just keep going
        # and show them at the end.

        for reservation, payment_method in reservations_to_process:
            is_creator = (
                self.flight_creator_user.account is not None and
                reservation.account == self.flight_creator_user.account
            )
            if is_creator:
                #add other costs to flight reservation
                reservation.set_anywhere_other_cost(self)

            due = reservation.calculate_anywhere_totalcost()

            with transaction.atomic():
                try:
                    charge = payment_method.charge(
                        due,
                        'Charge for RiseAnywhere Flight Reservation {reservation.pk} / Flight # {reservation.flight_numbers}'.format(reservation=reservation),
                        confirmed_by
                    )
                except GenericBillingException as E:
                    # we've already started processing cards, so delay failures til the end
                    # we could also refund all charges, or rewrite billing to authorize and charge in two passes...
                    reservations_failed.append((reservation, 'Charge {} failed: {}'.format(payment_method, E.message)))
                    continue

                reservation.charge = charge
                reservation.reserve(send_email=False)
                reservation.save()  # explicitly save despite reserve() also saving.


            # Not sending email inside the transaction because we don't want to reverse the transaction over failed email since
            # the card or bank account will already have been charged
            self.send_confirmation_email(reservation, payment_method)

        if reservations_failed:
            # Sentry will contain the locals() for this
            # TODO MVP : descriptive error for Rise agents

            # raising this error is already sort of descriptive
            raise ReservationError(
                'Failed to charge all Reservations',
                reservations_failed=reservations_failed
            )

    def send_confirmation_email(self, reservation, payment_method):

        title = "Rise Anywhere Reservation Confirmed"
        subject = "Rise Anywhere Reservation Confirmed"

        if isinstance(payment_method, BankAccount):
            payment_method_type = "bank account"
        else:
            payment_method_type = "credit card"


        context = {
            'leg1': self.leg1,
            'leg2': self.leg2,
            'seats': self.anywhere_request.seats,
            'public_key': self.public_key,
            'title': title,
            'seat_cost': reservation.calculate_anywhere_seat_cost(),
            'other_charges': reservation.calculate_anywhere_other_charges(),
            'other_desc': self.get_other_charge_description(),
            'tax': reservation.calculate_anywhere_tax(),
            'your_total': reservation.calculate_anywhere_totalcost(),
            'method_of_payment': payment_method_type
        }
        #only need one flight reservation to get passengers because they have to be the same on both
        flight_reservation = FlightReservation.objects.filter(reservation_id=reservation.id, reservation__account_id=reservation.account_id).first()
        passengers = Passenger.objects.filter(flight_reservation_id=flight_reservation.id).all()
        for passenger in passengers:
            to = [passenger.userprofile.email]
            #Flight creator may have passengers on his reservation that don't get the pricing details because the flight creator paid.
            #Two different templates for passengers NOT belonging to the reservation's account & for the person whose reservation it is.
            if passenger.userprofile.account_id == reservation.account_id:
                context['passengers'] = passengers
                send_html_email_task.delay('emails/anywhere_flight_confirmed', context, subject, settings.DEFAULT_FROM_EMAIL,
                                   to)
            else:
                context['passenger'] = passenger.user
                send_html_email_task.delay('emails/anywhere_flight_confirmed_no_prices', context, subject, settings.DEFAULT_FROM_EMAIL,
                                   to)

    def notify_of_manual_payment(self, reservation,user):
        """
        Notify RISE that a manual payment needs to be set up.
        Returns:

        """
        title="Manual Payment for Rise Anywhere Flight"
        context={
            'reservation': reservation,
            'flight_reservations': reservation.flightreservation_set.all(),
            'account': reservation.account,
            'user': user,
            'title': title,
            'subtotal': reservation.calculate_anywhere_seat_cost(),
            'tax_total': reservation.calculate_anywhere_tax(),
            'total_cost': reservation.calculate_anywhere_totalcost()
        }
        subject = title
        to_emails = settings.MANUAL_PAYMENT_NOTIFICATION_LIST

        send_html_email_task('emails/admin_manual_payment_notification', context, subject, settings.DEFAULT_FROM_EMAIL, to_emails)

    def perform_confirmation(self, confirmed_by):
        """
        entry point for confirmation flow
        """
        # step 1: transform reservations from pending to complete
        self.complete_reservations(confirmed_by)

        # step 2: ???

        # step 3: finalize
        self.confirmation_status = self.CONFIRMATION_STATUS_CONFIRMED

        self.save()

        if self.is_round_trip:
            self.leg1.anywhere_details.confirmation_status = self.leg1.anywhere_details.CONFIRMATION_STATUS_CONFIRMED
            self.leg2.anywhere_details.confirmation_status = self.leg2.anywhere_details.CONFIRMATION_STATUS_CONFIRMED
            self.leg1.anywhere_details.save()
            self.leg2.anywhere_details.save()
        else:
            self.leg1.anywhere_details.confirmation_status = self.leg1.anywhere_details.CONFIRMATION_STATUS_CONFIRMED
            self.leg1.anywhere_details.save()

    def get_other_charge_description(self):
        other_desc = self.leg1.anywhere_details.other_cost_desc
        if other_desc and self.leg2 and self.leg2.anywhere_details and self.leg2.anywhere_details.other_cost_desc:
            other_desc += " / %s" % self.leg2.anywhere_details.other_cost_desc
        elif self.leg2 and self.leg2.anywhere_details and self.leg2.anywhere_details.other_cost_desc:
            other_desc = self.leg2.anywhere_details.other_cost_desc
        return other_desc

    def is_refund_eligible(self, leg_id):
        '''
        A leg is only eligible for a refund if it is the first leg
        With new pricing logic all cost is lumped into 1st leg.
        Args:
            leg_id: the id of the leg to be cancelled

        Returns:

        '''
        if leg_id == self.leg1_id:
            return True

        return False

    def update_costs_after_admin_edit(self):
        """
        Call this when the admin edits the cost of a leg in a flightset.
        It updates both the full flight cost based on sum of legs and per seat cost based on avail seats &
        full flight cost
        It does NOT propagate down to anywhere flight detail  (like recalculate_seat_costs) because it gets called after the
        flight itself and its details are edited.
        Returns:

        """
        if self.is_round_trip:
            self.full_flight_cost = self.leg1.anywhere_details.full_flight_cost + self.leg2.anywhere_details.full_flight_cost
        else:
            self.full_flight_cost = self.leg1.anywhere_details.full_flight_cost

        seats_booked = self.total_seats - self.leg1.seats_available
        if seats_booked >= self.seats_required:
            next_seat = seats_booked+1
        else:
            next_seat = self.seats_required
        self.per_seat_cost = self.full_flight_cost / next_seat
        self.save()


    def __unicode__(self):
        return 'AnywhereFlightSet {self.pk} ({self.public_key})'.format(self=self)


ANYWHERE_PENDING_QUERYSET = AnywhereFlightRequest.objects.filter(status=AnywhereFlightRequest.STATUS_PENDING).exclude(depart_date__lt=datetime.datetime.now).order_by('depart_date')

auditlog.register(AnywhereRoute)
auditlog.register(AnywhereFlightRequest)
auditlog.register(AnywhereFlightSet)
