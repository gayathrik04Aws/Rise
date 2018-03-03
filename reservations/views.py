from django.conf import settings
from django.views.generic import View, TemplateView, DetailView, DateDetailView, FormView, RedirectView
from django.views.generic.detail import SingleObjectMixin
from django.core.urlresolvers import reverse_lazy
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.models import Group
from django.http import HttpResponse, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.utils.functional import cached_property

from datetime import date
import arrow
import calendar
import json
from collections import OrderedDict
import braintree
import stripe
from billing import paymentMethodUtil
from flights.models import Flight, Airport
from .models import FlightReservation, FlightWaitlist, ReservationError, Passenger
from accounts.models import User, UserProfile, Account, BillingPaymentMethod
from accounts.mixins import LoginRequiredMixin, PermissionRequiredMixin
from .mixins import ReservationMixin, CancellationMixin
from .forms import CompanionCountForm, CompanionSelectionForm, AddCompanionForm, SimplePaymentForm, AirportForm
from .forms import FilterResultsForm
from billing.models import Charge,Card,BankAccount
from anywhere.models import AnywhereFlightSet
import logging

logger = logging.getLogger(__name__)

stripe.api_key = settings.STRIPE_API_KEY


class BookTeamMemberView(LoginRequiredMixin, PermissionRequiredMixin, ReservationMixin, TemplateView):
    """
    Provide a view to select a team member

    Also accepts posts from modals
    """

    template_name = 'reservations/book/team_member.html'
    require_permissions = False
    permission_required = 'accounts.can_book_team'

    def post(self, request, *args, **kwargs):
        member_id = request.POST.get('member')
        member = next(iter(User.objects.filter(account=request.user.account, id=member_id)), None)
        self.set_booking_user(member)
        self.set_booking_userprofile(member.userprofile)

        return redirect('book_from')


class BookCompanionView(LoginRequiredMixin, PermissionRequiredMixin, ReservationMixin, TemplateView):
    """
    Provide a view to select a team member

    Also accepts posts from modals
    """

    template_name = 'reservations/book/team_member.html'
    require_permissions = False
    permission_required = 'accounts.can_manage_companions'

    def post(self, request, *args, **kwargs):
        # TODO:  When we start supporting dependent companions w/o user accounts this will have to work off profiles.
        member_id = request.POST.get('member')
        member = next(iter(User.objects.filter(account=request.user.account, id=member_id)), None)
        self.set_booking_user(member)
        self.set_booking_userprofile(member.userprofile)
        return redirect('book_from')

class BookFromView(LoginRequiredMixin, ReservationMixin, FormView):
    """
    A view to allow a user to choose where they want to fly from
    """

    template_name = 'reservations/book/from.html'
    form_class = AirportForm

    def get_context_data(self, **kwargs):
        context = super(BookFromView, self).get_context_data(**kwargs)

        plan = self.kwargs.get('plan', None)
        if plan:
            context.update({
                'plan': plan
            })

        return context

    def get(self, request, *args, **kwargs):
        self.clear_origin_airport()
        return super(BookFromView, self).get(request, *args, **kwargs)

    @cached_property
    def default_airport(self):
        """
        Gets the default airport (can be None if not set)

        Either the user profile airport, or last reservation made destination
        """

        if self.reservation:
            last_flight_reservation = next(iter(self.reservation.flightreservation_set.all().select_related('flight__destination').only('flight__destination').order_by('-id')[:1]), None)
            if last_flight_reservation:
                return last_flight_reservation.flight.destination

        airport = self.request.user.user_profile.origin_airport

        if airport is not None:
            return airport

        return next(iter(Airport.objects.all()[:1]), None)

    def get_initial(self):
        """
        Returns the initial data to use for forms on this view.
        """
        return {
            'airport': self.default_airport,
        }

    def form_valid(self, form):
        airport = form.cleaned_data.get('airport')

        self.set_origin_airport(airport)

        return redirect('book_when', airport.code)


class BookCalendarView(LoginRequiredMixin, ReservationMixin, DetailView):

    template_name = 'reservations/book/calendar.html'
    model = Airport
    slug_field = 'code'
    slug_url_kwarg = 'code'
    context_object_name = 'origin'

    def get(self, request, *args, **kwargs):
        self.clear_booking_date()
        self.object = self.get_object()

        if self.origin_airport is None or self.origin_airport.pk != self.object.pk:
            self.set_origin_airport(self.object)

        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    @cached_property
    def year(self):
        year = self.kwargs.get('year')
        if year is None:
            year = arrow.now().year

        return int(year)

    @cached_property
    def month(self):
        month = self.kwargs.get('month')
        if month is None:
            month = arrow.now().month
        return int(month)

    def get_context_data(self, **kwargs):
        context = super(BookCalendarView, self).get_context_data(**kwargs)

        origin = self.object

        # get the current day time
        now = arrow.now()
        if now.year == self.year and now.month == self.month:
            start_date = now
        else:
            start_date = now.replace(year=self.year, month=self.month, day=1)

        next_date = start_date.replace(months=1, day=1).floor('day')
        previous_date = start_date.replace(months=-1, day=1).floor('day')

        if previous_date < now.replace(day=1).floor('day'):
            previous_date = None

        cal = calendar.Calendar(calendar.SUNDAY)
        results = OrderedDict()

        for day in cal.itermonthdates(self.year, self.month):
            results[day] = None

        first_day, days_in_month = calendar.monthrange(self.year, self.month)

        end_date = start_date.replace(day=days_in_month).ceil('day').datetime

        flight_results = Flight.search.get_availability_for_date_range(origin, start_date.datetime, end_date, self.booking_userprofile, self.companion_count)

        results.update(flight_results)

        context.update({
            'today': now.date(),
            'results': results,
            'start_date': start_date,
            'next_date': next_date,
            'previous_date': previous_date,
        })

        return context


class BookFlightsView(LoginRequiredMixin, ReservationMixin, DateDetailView):
    """
    A view to display all flights on a given day from a given origin to allow a user to book one.
    """

    template_name = 'reservations/book/flights.html'
    allow_future = True
    model = Airport
    slug_field = 'code'
    slug_url_kwarg = 'code'
    context_object_name = 'origin'
    month_format = '%m'
    form_class = CompanionCountForm

    def _make_single_date_lookup(self, date):
        """
        Disables queryset lookup date args, but still allows us to use the date features of this CBV
        """
        return {}

    @cached_property
    def flight_date(self):
        return date(int(self.get_year()), int(self.get_month()), int(self.get_day()))

    def get(self, request, *args, **kwargs):
        self.set_booking_date(self.flight_date)
        return super(BookFlightsView, self).get(request, *args, **kwargs)

    def get_context_data(self,  **kwargs):
        context = super(BookFlightsView, self).get_context_data(**kwargs)

        flights = Flight.search.get_flights_for_date(self.object, self.flight_date, self.booking_userprofile, companion_count=self.companion_count, user_is_not_flying=self.companions_only)

        context.update({
            'date': self.flight_date,
            'flights': flights,
            'reservation': self.reservation,
            'companion_form':CompanionCountForm(initial={'companion_count': self.companion_count, 'companions_only': self.companions_only}),
            'filter_results_form': FilterResultsForm(initial={'filter': self.companion_count}),
        })

        return context

    def post(self, request, *args, **kwargs):
        """
        Handles POST requests, instantiating a form instance with the passed
        POST variables and then checked for validity.
        """
        if 'companion_count' in request.POST:
            companion_form = CompanionCountForm(request.POST)
            if companion_form.is_valid():

                if companion_form.cleaned_data and "companion_count" in companion_form.cleaned_data:
                    companion_count = companion_form.cleaned_data.get('companion_count', 0)
                    self.set_companion_count(int(companion_count))
                else:
                    # default it for now
                    companion_form.cleaned_data["companion_count"]=0
                    self.set_companion_count(0)
                if companion_form.cleaned_data and "companions_only" in companion_form.cleaned_data:
                    companions_only = companion_form.cleaned_data.get('companions_only')
                    self.set_companions_only(bool(companions_only))
                else:
                    #default it for now
                    companion_form.cleaned_data["companions_only"] = False
                    self.set_companions_only(False)
                return redirect(request.path)
            else:
                # only the companions_only combo could be wrong.
                messages.error(request, "You must select at least one companion or uncheck the 'I am not flying...' option.")
                return redirect(request.path)

        elif 'flight' in request.POST:
            flight_pk = request.POST.get('flight')
            if not flight_pk or not flight_pk.isdigit():
                messages.error(request, 'Please select a flight.')
                return redirect(request.path)

            flight = get_object_or_404(Flight, pk=flight_pk)

            # if the flight is full, waitlist them instead.
            if self.companions_only:
                pax = self.companion_count
            else:
                pax = 1+self.companion_count
            is_available = flight.check_plan_restrictions(self.booking_userprofile, self.companion_count) and flight.check_plan_seat_restrictions(self.booking_userprofile, pax)
            if flight.is_flight_full(self.booking_userprofile, self.companion_count, self.companions_only) or not is_available:
                return redirect('flight_waitlist', pk=flight.pk)

            # if companions only this reserve
            flight_reservation = flight.reserve_flight(request.user, self.booking_userprofile, self.reservation, self.companion_count, self.companions_only)

            if flight_reservation is not None:
                self.set_reservation(flight_reservation.reservation)

                if flight_reservation.passenger_count > 1 or self.companions_only:
                    return redirect('book_companions', pk=flight_reservation.pk)

                if 'complete' in request.POST:
                    return redirect('book_confirm')
                else:
                    return redirect('book_from')

            messages.error(request, 'There was an error booking your requested flight. Please try again or choose another flight.')
            return redirect('book_flights', code=flight.origin.code, year=flight.departure.year, month=flight.departure.month, day=flight.departure.day)

        return redirect(request.path)


class JoinFlightWaitlistView(LoginRequiredMixin, ReservationMixin, View):
    """
    A view to join the waitlist for a full/unavailable flight
    """

    def get(self, request, *args, **kwargs):
        flight_pk = self.kwargs.get('pk')
        flight = get_object_or_404(Flight, pk=flight_pk)
        existingObj = FlightWaitlist.objects.filter(userprofile=self.booking_userprofile, flight=flight).all()

        if existingObj:
            obj = existingObj.first()
            if obj.status==FlightWaitlist.STATUS_WAITING:
                alreadyWaiting = True
                alreadyBooked = False
            elif obj.status==FlightWaitlist.STATUS_RESERVED:
                alreadyWaiting = False
                alreadyBooked = False
                # see if they are already booked; they may have been on flight, canceled, re-wishlisted.
                frs = FlightReservation.objects.filter(flight=flight, reservation__account=self.booking_userprofile.account).all()
                for fr in frs:
                    if fr.status != FlightReservation.STATUS_CANCELLED:
                        isPassenger = fr.passenger_set.filter(userprofile=self.booking_userprofile).count() > 0
                        if isPassenger:
                            alreadyBooked = True
                            break
            else:
                alreadyWaiting = False
                alreadyBooked = False
        else:
            alreadyWaiting = False
            alreadyBooked = False

        flight_waitlist, created = FlightWaitlist.objects.get_or_create(userprofile=self.booking_userprofile, flight=flight, user=self.booking_user)

        if not alreadyBooked and not alreadyWaiting or created:
            flight_waitlist.status = FlightWaitlist.STATUS_WAITING
            flight_waitlist.passenger_count=self.companion_count if self.companion_count else 0
            flight_waitlist.save()
            messages.info(request, 'The flight you selected is full. <br><br> You have been placed on the Wishlist meaning, <br><br>  1) our RISE Ops team is now hard at work analyzing every potential solution to accommodate your current and future flight needs and,<br><br> 2) you will be notified if a spot on this flight becomes available.<br><br>  Thank you for providing us with this invaluable insight as we strive to build an even better RISE.')
        if alreadyWaiting:
            flight_waitlist.passenger_count = self.companion_count if self.companion_count else 0
            flight_waitlist.save()
            messages.info(request, 'It looks like you are already on the Wishlist for Flight %s from %s-%s on %s. <br><br> We are hard at work analyzing every potential solution to accommodate your current and future flight needs and you will be notified if a spot on this flight becomes available. <br><br>  Thank you for providing us with this invaluable insight as we strive to build an even better RISE.' % (flight.flight_number,flight.origin.code, flight.destination.code, flight.local_departure_display()))
        if alreadyBooked:
            messages.error(request, 'You are already booked on this flight.' )
            return redirect('book_flights', code=flight.origin.code, year=flight.local_departure_year_digit(), month=flight.local_departure_month_digit(), day=flight.local_departure_day_digit())

        flight_waitlist.send_waitlist_email()

        return redirect('book_flights', code=flight.origin.code, year=flight.local_departure_year_digit(), month=flight.local_departure_month_digit(), day=flight.local_departure_day_digit())

    def is_upgrade(self):
        """
        Returns true if this user should be prompted to upgrade their account
        """
        user = self.request.user
        # corporate accounts cannot upgrade plans
        if user.account.is_corporate():
            return False

        # if the user is not on the express plan, dont show
        if user.account.plan.name not in ('Express',):
            return False

        # if the user cannot manage plan, return false
        if not user.has_perm('accounts.can_manage_plan'):
            return False

        return True

    def post(self, request, *args, **kwargs):
        flight_pk = self.kwargs.get('pk')
        flight = get_object_or_404(Flight, pk=flight_pk)

        flight_waitlist, created = FlightWaitlist.objects.get_or_create(userprofile=self.booking_userprofile, flight=flight, passenger_count=self.companion_count if self.companion_count else 0)
        flight_waitlist.status = FlightWaitlist.STATUS_WAITING
        flight_waitlist.save()
        flight_waitlist.send_waitlist_email()

        data = {
            'flight_waitlist': flight_waitlist,
        }

        if self.is_upgrade():
            template = 'reservations/book/waitlist_upgrade.html'
        else:
            template = 'reservations/book/waitlist_modal.html'

        return TemplateResponse(self.request, template, data, content_type='text/html')


class FlightWaitlistCancelView(LoginRequiredMixin, ReservationMixin, View):
    """
    Admin deletes waitlist entry via pk
    """

    def get(self, request, *args, **kwargs):
        """
        Handle GET requests.  Gets waitlist pk and deletes it
        """
        waitlist_pk = self.kwargs.get('pk', None)
        if waitlist_pk:
            waitlist = get_object_or_404(FlightWaitlist, id=waitlist_pk)
            # verify this waitlist is for current user's account
            if waitlist.userprofile.account == self.request.user.account:
                waitlist.status = FlightWaitlist.STATUS_CANCELLED
                waitlist.save()
                messages.info(request, 'You have been removed from the wishlist for flight %s.' % waitlist.flight.flight_number)
                pass
            else:
                messages.error(request, 'You do not have permission to cancel this wishlist request.')

        return HttpResponseRedirect(self.request.META['HTTP_REFERER'])


class CompanionSelectionView(LoginRequiredMixin, ReservationMixin, SingleObjectMixin, FormView):
    """
    A view to select which companions are also on the flight.
    """

    template_name = 'reservations/book/companions.html'
    reservation_required = True
    form_class = CompanionSelectionForm
    model = FlightReservation
    context_object_name = 'flight_reservation'

    def get_queryset(self):
        """
        Ensure this flight reservation belongs to their user account
        """
        return FlightReservation.objects.filter(reservation__account__id=self.request.user.account_id)

    def get_initial(self):
        initial = super(CompanionSelectionView, self).get_initial()

        initial.update({
            'companions': [c.userprofile for c in self.get_object().get_companions()],
        })

        return initial

    def get_form_kwargs(self):
        kwargs = super(CompanionSelectionView, self).get_form_kwargs()

        kwargs.update({
            'account': self.request.user.account,
            'count': self.companion_count,
        })

        return kwargs

    def form_valid(self, form):
        companions = form.cleaned_data.get('companions')
        flight_reservation = self.get_object()
        flight_reservation.clear_companions()
        for companion in companions:
            flight_reservation.add_passenger(companion, companion=True)
        return redirect('book_confirm')

    def get_context_data(self, **kwargs):
        self.object = self.get_object()
        context = super(CompanionSelectionView, self).get_context_data(**kwargs)
        userpassenger = Passenger.objects.filter(flight_reservation_id=self.object.id, userprofile_id=self.request.user.userprofile.id).first()
        if userpassenger:
            context["user_is_flying"] = True
        else:
            context["user_is_flying"] = False
        return context


class AddCompanionView(LoginRequiredMixin, ReservationMixin, PermissionRequiredMixin, SingleObjectMixin, FormView):
    """
    Add a companion
    """
    permission_required = 'accounts.can_manage_companions'
    template_name = 'reservations/book/add_companion.html'
    reservation_required = True
    form_class = AddCompanionForm
    model = FlightReservation
    context_object_name = 'flight_reservation'
    success_url = reverse_lazy('book_companions')

    def get_queryset(self):
        """
        Ensure this flight reservation belongs to their user account
        """
        return FlightReservation.objects.filter(reservation__account__id=self.request.user.account_id)

    def get_form_kwargs(self):
        kwargs = super(AddCompanionView, self).get_form_kwargs()

        kwargs.update({
            'account': self.request.user.account,
            'count': self.companion_count,
        })

        return kwargs

    def get_context_data(self, **kwargs):
        self.object = self.get_object()
        context = super(AddCompanionView, self).get_context_data(**kwargs)

        return context

    def form_valid(self, form):
        flight_reservation = self.get_object()

        first_name = form.cleaned_data.get('first_name').strip()
        last_name = form.cleaned_data.get('last_name')
        email = form.cleaned_data.get('email')
        phone = form.cleaned_data.get('phone').strip()
        mobile_phone = form.cleaned_data.get('mobile_phone').strip()
        date_of_birth = form.cleaned_data.get('date_of_birth')
        weight = form.cleaned_data.get('weight').strip()

        if form.account:
            user_profile_obj = UserProfile.objects.create(first_name=first_name, last_name=last_name, email=email,
                                                          account=form.account, phone=phone, mobile_phone=mobile_phone,
                                                          date_of_birth=date_of_birth, weight=weight)


            user_profile_obj.save()
            if user_profile_obj.email:
                companion_obj = User.objects.create(first_name=first_name, last_name=last_name, email=email,
                                                          account=form.account, userprofile=user_profile_obj)
                companion_obj.save()
                companion_group = Group.objects.get(name='Companion')
                companion_group.user_set.add(companion_obj)

        return redirect('book_companions', pk=flight_reservation.id)


class BookConfirmView(LoginRequiredMixin, ReservationMixin, FormView):
    """
    A view to confirm your reservation or continue adding flights
    """

    reservation_required = True
    template_name = 'reservations/book/confirm.html'
    form_class = SimplePaymentForm
    success_url = reverse_lazy('book_reserve')

    def get(self, request, *args, **kwargs):
        if self.reservation.flightreservation_set.count() == 0:
            return redirect('book_from')
        return super(BookConfirmView, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(BookConfirmView, self).get_context_data(**kwargs)
        bill_pay_methods = BillingPaymentMethod.objects.filter(account=self.request.user.account).all()
        cards = Card.objects.filter(account=self.request.user.account).all()
        bankaccounts = BankAccount.objects.filter(account=self.request.user.account,verified=True).all()
        paylist = []

        if cards is not None:
            for card in cards:
                paymethod = bill_pay_methods.filter(id=card.billing_payment_method_id).first()
                payment = {
                    "id":paymethod.id,
                    "is_default":paymethod.is_default,
                    "text":"Credit Card ending with " + card.last4,
                    "nickname":paymethod.nickname
                }
                paylist.append(payment)
        if bankaccounts is not None:
            for bankaccount in bankaccounts:
                paymethod = bill_pay_methods.filter(id=bankaccount.billing_payment_method_id).first()
                payment = {
                    "id":paymethod.id,
                    "is_default":paymethod.is_default,
                    "text":"Bank Account ending with " + bankaccount.last4,
                    "nickname":paymethod.nickname
                }
                paylist.append(payment)

        if self.request.user.account.has_braintree():
            client_token = braintree.ClientToken.generate({'customer_id': self.request.user.account.braintree_customer_id})
        else:
            client_token = braintree.ClientToken.generate()

        context.update({
            'client_token': client_token,
            'reservation': self.reservation,
            'STRIPE_PUBLISHABLE_KEY': settings.STRIPE_PUBLISHABLE_KEY,
            'paylist': paylist,
        })

        return context

    def form_valid(self, form):
        user = self.request.user
        reservation = self.reservation
        # if this reservation requires a payment
        if reservation.requires_payment():
            payment_method = self.request.POST.get('payment_method')
            # get the stripe amount to charge
            amount = reservation.total_amount()
            payment_method_nonce = form.cleaned_data.get('payment_method_nonce')
            # if no new card has been added or there is no existing card or bank account show error
            if (not payment_method_nonce and payment_method is None):
                messages.error(self.request, 'Please provide payment information.')
                return self.form_invalid(form)

            description = 'Charge for reservation %s' % (reservation.pk,)
            # The payment type selected is an existing credit card or bank account
            if not payment_method_nonce and payment_method is not None :
                try:
                    bill_pay_method = BillingPaymentMethod.objects.filter(id=payment_method).first()
                    if bill_pay_method.payment_method == BillingPaymentMethod.PAYMENT_CREDIT_CARD:
                        # The payment selected is an existing credit card.
                        # The credit card transactions will go through braintree
                        card = Card.objects.filter(billing_payment_method=bill_pay_method).first()
                        charge = card.charge(amount, description, user)
                    else:
                        # The payment selected is an existing bank account.
                        # The bank transactions will go through stripe
                        bankaccount = BankAccount.objects.filter(billing_payment_method=bill_pay_method).first()
                        charge = bankaccount.charge(amount, description, user)
                except Exception as e:
                    messages.error(self.request, e.message)
                    return self.form_invalid(form)
                reservation.charge = charge
                reservation.save()
                return super(BookConfirmView, self).form_valid(form)
            # The user added a new credit card for payment.
            elif payment_method_nonce:
                #check if the user has an existing brain tree customer id and no credit card on his account
                # The new credit card is stored in the user account
                try:
                    nickname = form.cleaned_data.get('nickname')
                    card = paymentMethodUtil.createCreditCard(payment_method_nonce, False, user.account.id, nickname)
                except paymentMethodUtil.CardException as e:
                    for error in e.message:
                        form.add_error(None,error)
                    return self.form_invalid(form)
                if user.account.payment_method is None:
                    user.account.payment_method = Account.PAYMENT_CREDIT_CARD
                    user.account.save()
                description = 'Charge for reservation %s' % (reservation.pk,)
                charge = card.charge(amount, description, user)
                #if there is an existing credit card but wants to use a different card for the payment
                reservation.charge = charge
                reservation.save()
                return super(BookConfirmView, self).form_valid(form)

            messages.error(self.request, 'Please provide payment information.')
            return self.form_invalid(form)

        return super(BookConfirmView, self).form_valid(form)


class ConfirmReservationView(LoginRequiredMixin, ReservationMixin, View):
    """
    A view to reserve a flight and redirect to confirm view
    """
    reservation_required = True

    def get(self, request, *args, **kwargs):
        # if payment is requried, check to make sure
        if self.reservation.requires_payment() and self.reservation.charge is None:
            messages.error(self.request, 'Please provide payment information.')
            return redirect('book_confirm')
        self.reservation.reserve()
        return redirect('book_confirmed')


class BookConfirmationView(LoginRequiredMixin, ReservationMixin, TemplateView):
    """
    A view which displays the confirmed reservation
    """
    reservation_required = True
    redirect_name = 'dashboard'
    template_name = 'reservations/book/confirmation.html'

    def get_context_data(self, **kwargs):
        context = super(BookConfirmationView, self).get_context_data(**kwargs)

        context.update({
            'reservation': self.reservation,
        })

        self.clear_reservation()
        self.clear_companion_count()
        self.clear_companions_only()
        self.clear_booking_user()
        self.clear_booking_userprofile()
        return context


class ReservationTimeRemainingView(LoginRequiredMixin, ReservationMixin, View):
    """
    A view to return the amount of time remaining on a reservation.
    """

    auto_renew = False
    reservation_required = True
    redirect_name = None

    def get(self, request, *args, **kwargs):
        total_seconds = self.reservation.seconds_remaining()
        minutes = total_seconds / 60
        seconds = total_seconds % 60

        data = {
            'total_seconds': total_seconds,
            'minutes': minutes,
            'seconds': seconds,
            'formatted': '%d:%02d' % (minutes, seconds),
        }

        return HttpResponse(json.dumps(data), content_type='application/json')


class BookRenewReservationView(LoginRequiredMixin, ReservationMixin, View):
    """
    A view which allows renewing of a reservation via AJAX

    Will auto renew the reservation via the reservation mixin
    """
    reservation_required = True

    def get(self, request, *args, **kwargs):
        return HttpResponse()


class CancelBookingView(LoginRequiredMixin, ReservationMixin, View):
    """
    A view to cancel the reservation during booking
    """

    def get(self, request, *args, **kwargs):
        if self.reservation is not None:
            self.reservation.cancel()
        self.clear_all()

        return redirect('dashboard')


class CancelFlightReservationView(LoginRequiredMixin, CancellationMixin, SingleObjectMixin, View):
    """
    A view to cancel a flight reservation either via AJAX or URL
    """

    model = FlightReservation

    def get(self, request, *args, **kwargs):
        flight_reservation = self.get_object()

        reservation_id = flight_reservation.reservation.id
        account_id = flight_reservation.reservation.account_id

        flight_reservation.cancel(user=request.user)

        if request.is_ajax():
            account = Account.objects.get(id=account_id)
            flight_reservation_count = FlightReservation.objects.filter(reservation__id=reservation_id).count()
            data = {
                'flight_reservation_count': flight_reservation_count,
                'total_available_companion_passes': account.total_available_companion_passes(),
                'total_available_passes': account.total_available_passes()
            }

            return HttpResponse(json.dumps(data), content_type='application/json')

        if 'next' in request.GET:
            return redirect(request.GET.get('next'))

        return redirect('book_from')


class BookSimilarFlightsView(LoginRequiredMixin, ReservationMixin, TemplateView):
    """
    A view to allow a user to book a similar flight based on a Flight or a Flight Reservation
    """
    template_name = 'reservations/book/similar_flights.html'
    allow_future = True
    model = Airport
    slug_field = 'code'
    slug_url_kwarg = 'code'
    context_object_name = 'origin'
    month_format = '%m'
    form_class = CompanionCountForm

    def get_context_data(self, **kwargs):
        context = super(BookSimilarFlightsView, self).get_context_data(**kwargs)

        flight_pk = self.kwargs.get('flight_pk', None)
        flightreservation_pk = self.kwargs.get('flightreservation_pk', None)

        if flight_pk:
            flight = get_object_or_404(Flight, pk=flight_pk)
        elif flightreservation_pk:
            flight_reservation = get_object_or_404(FlightReservation, pk=flightreservation_pk)
            flight = flight_reservation.flight

        flights = Flight.search.get_similar_flights(flight, self.request.user.userprofile, self.companion_count)

        context.update({
            'origin_airport': flight.origin,
            'destination_airport': flight.destination,
            'flights': flights,
            'reservation': self.reservation,
            'companion_form': CompanionCountForm(initial={'companion_count': self.companion_count}),
        })

        return context

    def post(self, request, *args, **kwargs):
        """
        Handles POST requests, instantiating a form instance with the passed
        POST variables and then checked for validity.
        """
        if 'companion_count' in request.POST:
            companion_form = CompanionCountForm(data=request.POST, initial={'companion_count': self.companion_count})
            if companion_form.is_valid():
                companion_count = companion_form.cleaned_data.get('companion_count', 0)
                self.set_companion_count(int(companion_count))
                return redirect(request.path)
            else:
                return self.render_to_response(self.get_context_data(companion_form=companion_form))

        elif 'flight' in request.POST:
            flight_pk = request.POST.get('flight')
            if not flight_pk or not flight_pk.isdigit():
                messages.error(request, 'Please select a flight.')
                return redirect(request.path)

            flight = get_object_or_404(Flight, pk=flight_pk)

            flight_reservation = flight.reserve_flight(request.user, self.booking_userprofile, self.reservation, self.companion_count)

            if flight_reservation is not None:
                self.set_reservation(flight_reservation.reservation)

                if flight_reservation.passenger_count > 1:
                    return redirect('book_companions', pk=flight_reservation.pk)

                if 'complete' in request.POST:
                    return redirect('book_confirm')
                else:
                    return redirect('book_from')

            messages.error(request, 'There was an error booking your requested flight. Please try again or choose another flight.')
            return redirect('book_flights', code=flight.origin.code, year=flight.departure.year, month=flight.departure.month, day=flight.departure.day)

        return redirect(request.path)

class BookAnywhereByFlightIDView(RedirectView):
    pattern_name = 'book_anywhere'
    model = AnywhereFlightSet

    def get_redirect_url(self, *args, **kwargs):
        """
        Redirect to booking if they are logged in.
        Redirect to login/signup if they are not.
        We have to put the flight id in session just in case they end up in signup.
        """
        flight_id = self.kwargs.get('pk')
        flightset = AnywhereFlightSet.objects.filter(leg1_id=flight_id).first()
        if flightset is None:
            flightset = AnywhereFlightSet.objects.filter(leg2_id=flight_id).first()
        if flightset is None:
            messages.error(self.request, "Flight is not an Anywhere flight.")
            return redirect(self.request.path)

        return reverse_lazy(self.pattern_name,kwargs={'slug': flightset.public_key})

class BookAnywhereView(LoginRequiredMixin,TemplateView, ReservationMixin):
    """
    Placeholder for Anywhere booking - to be implemented.
    """
    template_name = 'reservations/book/book_anywhere_flight.html'
    month_format = '%m'
    model = Airport

    def get_context_data(self, **kwargs):
        context = super(BookAnywhereView,self).get_context_data(**kwargs)
        public_key = self.kwargs["slug"]
        flightset = AnywhereFlightSet.objects.filter(public_key=public_key).first()
        context.update({
            'origin_airport': flightset.origin,
            'destination_airport': flightset.destination,
            'flightset': flightset,
            'verify': self.request.GET.get('v','none')
        })
        return context

    def post(self, request, *args, **kwargs):
        """
        Handles POST requests, instantiating a form instance with the passed
        POST variables and then checked for validity.
        """
        if 'flightset' in request.POST:

            flightset_key = request.POST.get('flightset')
            flightset = AnywhereFlightSet.objects.filter(public_key=flightset_key).first()
            if not flightset:
                messages.error(request, 'There was an error booking your requested flight.  Please try again or choose another flight.')
                return redirect(request.path)

            userprofile = self.request.user.userprofile
            if flightset.leg1.is_booked_by_user(userprofile):
                messages.error(request, 'You are already booked on this flight.')
                return redirect(request.path)

            flight_reservation = flightset.reserve_seats(userprofile, 1, self.request.user)
            if not flight_reservation:
                messages.error(request, "There was an error booking the reservation.")
                return redirect(request.path)

            verify=request.POST.get('verify','none')
            if verify=="m":
                #send email notifying of manual anywhere reservation.
                flightset.notify_of_manual_payment(flight_reservation, self.request.user)
            if flight_reservation is not None:
                self.set_reservation(flight_reservation)
                # if this flightset is already confirmed, auto-confirm & charge.
                # the flightset complete reservations looks for unconfirmed reservations only so won't
                # affect anything previously done
                try:
                    if flightset.confirmation_status == AnywhereFlightSet.CONFIRMATION_STATUS_CONFIRMED:
                        flightset.complete_reservations(self.request.user)
                except ReservationError as re:
                    # swallow this error because it's irrelevant to user;  TODO log it instead.
                    logger.exception('Error completing reservations for RISE ANYWHERE flightset %s' % str(flightset.id))
                    logger.exception(re)

                # if the flight had previously been confirmed but is now full, then other passengers need refunds because
                # they paid more. If flight wasn't already confirmed no one has paid yet so nothing to refund.
                if flightset.leg1.seats_available == 0 and flightset.confirmation_status == flightset.CONFIRMATION_STATUS_CONFIRMED:
                    # refunds may be due
                    try:
                        flightset.update_final_costs()
                        #we don't send user in here because the person buying the seat isn't actually pushing the refunds
                        flightset.process_overpaid_passenger_refunds(None)
                    except ReservationError as re:
                        # just log it, email already went out
                        logger.exception('Error processing refunds for RISE ANYWHERE flightset %s'% str(flightset.id))
                        logger.exception(re)


                url = "%s?%s%s" % (reverse_lazy('book_anywhere_confirmed', kwargs={"slug":flightset_key}), "v=", verify)
                return redirect(url )

            messages.error(request, 'There was an error booking your requested flight. Please try again or choose another flight.')
            return redirect('anywhere_index')

        return redirect(request.path)

class BookAnywhereConfirmationView(LoginRequiredMixin, TemplateView, ReservationMixin):
    template_name = 'reservations/book/book_anywhere_confirmation.html'

    def get_context_data(self, **kwargs):
        context = super(BookAnywhereConfirmationView,self).get_context_data(**kwargs)
        public_key = self.kwargs["slug"]
        flightset = AnywhereFlightSet.objects.filter(public_key=public_key).first()
        context.update({
            'origin_airport': flightset.origin,
            'destination_airport': flightset.destination,
            'flightset': flightset,
            'reservation': self.reservation,
            'verify': self.request.GET.get('v','')
        })
        return context

class BookFlightView(LoginRequiredMixin, ReservationMixin, TemplateView):
    """
    A view to allow a user to book a given flight
    """
    template_name = 'reservations/book/book_flight.html'
    allow_future = True
    model = Airport
    slug_field = 'code'
    slug_url_kwarg = 'code'
    context_object_name = 'origin'
    month_format = '%m'
    form_class = CompanionCountForm

    def get_context_data(self, **kwargs):
        context = super(BookFlightView, self).get_context_data(**kwargs)

        flight_pk = self.kwargs.get('flight_pk', None)

        if flight_pk:
            flight = get_object_or_404(Flight, pk=flight_pk)

        flights = Flight.search.get_single_flight(flight, self.request.user.userprofile, self.companion_count)

        context.update({
            'flight': flight,
            'origin_airport': flight.origin,
            'destination_airport': flight.destination,
            'flights': flights,
            'reservation': self.reservation,
            'companion_form': CompanionCountForm(initial={'companion_count': self.companion_count}),
        })

        return context

    def get(self, request, *args, **kwargs):
        response = super(BookFlightView, self).get(self, request, *args, **kwargs)

        context = self.get_context_data(**kwargs)

        if not context['flights']:
            messages.error(self.request, 'Flight %s is not reservable' % context['flight'].flight_number)
            return redirect('dashboard')
        else:
            return response

    def post(self, request, *args, **kwargs):
        """
        Handles POST requests, instantiating a form instance with the passed
        POST variables and then checked for validity.
        """
        if 'companion_count' in request.POST:
            companion_form = CompanionCountForm(data=request.POST, initial={'companion_count': self.companion_count})
            if companion_form.is_valid():
                companion_count = companion_form.cleaned_data.get('companion_count', 0)
                self.set_companion_count(int(companion_count))
                return redirect(request.path)
            else:
                return self.render_to_response(self.get_context_data(companion_form=companion_form))

        elif 'flight' in request.POST:
            flight_pk = request.POST.get('flight')
            if not flight_pk or not flight_pk.isdigit():
                messages.error(request, 'Please select a flight.')
                return redirect(request.path)

            flight = get_object_or_404(Flight, pk=flight_pk)

            flight_reservation = flight.reserve_flight(request.user, self.booking_userprofile, self.reservation, self.companion_count)

            if flight_reservation is not None:
                self.set_reservation(flight_reservation.reservation)

                if flight_reservation.passenger_count > 1:
                    return redirect('book_companions', pk=flight_reservation.pk)

                if 'complete' in request.POST:
                    return redirect('book_confirm')
                else:
                    return redirect('book_from')

            messages.error(request, 'There was an error booking your requested flight. Please try again or choose another flight.')
            return redirect('book_flights', code=flight.origin.code, year=flight.departure.year, month=flight.departure.month, day=flight.departure.day)

        return redirect(request.path)


class RescheduleFlightView(LoginRequiredMixin, ReservationMixin, TemplateView):
    """
    A view to allow a user to reschedule a flight while canceling the current one
    """
    template_name = 'reservations/book/similar.html'

    model = Airport
    slug_field = 'code'
    slug_url_kwarg = 'code'
    context_object_name = 'origin'

    @cached_property
    def year(self):
        year = self.kwargs.get('year')
        if year is None:
            year = arrow.now().year

        return int(year)

    @cached_property
    def month(self):
        month = self.kwargs.get('month')
        if month is None:
            month = arrow.now().month
        return int(month)

    def get_context_data(self, **kwargs):
        context = super(RescheduleFlightView, self).get_context_data(**kwargs)

        flight_pk = self.kwargs.get('pk', None)
        if flight_pk:
            flight_obj = next(iter(Flight.objects.filter(id=flight_pk)), None)
            origin = flight_obj.origin
            destination = flight_obj.destination
            flight_reservation = next(iter(FlightReservation.objects.filter(flight=flight_obj)), None)
            reservation = flight_reservation.reservation

            flight_reservation.cancel()

            # get the current day time
            now = arrow.now()
            if now.year == self.year and now.month == self.month:
                start_date = now
            else:
                start_date = now.replace(year=self.year, month=self.month, day=1)

            next_date = start_date.replace(months=1, day=1).floor('day')
            previous_date = start_date.replace(months=-1, day=1).floor('day')

            if previous_date < now.replace(day=1).floor('day'):
                previous_date = None

            cal = calendar.Calendar()
            results = OrderedDict()

            for day in cal.itermonthdates(self.year, self.month):
                results[day] = None

            first_day, days_in_month = calendar.monthrange(self.year, self.month)

            end_date = start_date.replace(day=days_in_month).ceil('day').datetime

            flight_results = Flight.search.get_availability_for_date_range(origin, start_date.datetime, end_date, self.booking_userprofile, self.companion_count, destination)

            results.update(flight_results)

            context.update({
                'origin': origin,
                'today': now.date(),
                'results': results,
                'reservation': reservation,
                'start_date': start_date,
                'next_date': next_date,
                'previous_date': previous_date,
            })

        return context
