from django.conf import settings
from django.contrib import messages
from django.core.urlresolvers import reverse_lazy
from django.http import HttpResponse, HttpResponseRedirect
from django.db import transaction
from django.db.models import Q
from django.shortcuts import redirect
from django.views.generic import DetailView, ListView, FormView, View, TemplateView
from django.views.generic.detail import SingleObjectMixin
from django.shortcuts import get_object_or_404

import unicodecsv
import arrow
from datetime import datetime, timedelta
import json
import stripe
import braintree
from accounts.models import Account, BillingPaymentMethod
from accounts.mixins import StaffRequiredMixin, PermissionRequiredMixin

from announcements.models import AutomatedMessage
from billing.models import Charge,Card,BankAccount
from billing import paymentMethodUtil

from .forms import SimplePaymentForm, CompanionSelectionForm
from .admin_forms import BookWithoutPaymentForm
from flights.models import Flight
from .models import FlightWaitlist, FlightReservation, Passenger
from .admin_mixins import AdminReservationMixin


class AdminFlightReservationDetailView(StaffRequiredMixin, PermissionRequiredMixin, DetailView):
    """
    Detail view for a flight reservation
    """

    permission_required = 'accounts.can_view_members'
    model = FlightReservation
    template_name = 'admin/reservations/flightreservation_detail.html'


class AdminFlightWaitlistListView(StaffRequiredMixin, PermissionRequiredMixin, ListView):
    """
    Admin FlightWaitlist list
    """

    permission_required = 'accounts.can_book_members'
    model = FlightWaitlist
    template_name = 'reservations/admin/waitlist.html'

    def get_queryset(self):
        qs = FlightWaitlist.objects.filter(status=FlightWaitlist.STATUS_WAITING) \
            .exclude(flight__status__in=(Flight.STATUS_CANCELLED, Flight.STATUS_COMPLETE, Flight.STATUS_IN_FLIGHT)) \
            .select_related('userprofile', 'userprofile__account', 'flight',) \
            .order_by('flight', 'flight__departure', 'created')

        search_term = self.request.GET.get('s')
        if search_term:
            qs = qs.filter(
                Q(userprofile__first_name__icontains=search_term) |
                Q(userprofile__last_name__icontains=search_term) |
                Q(flight__flight_number__icontains=search_term) |
                Q(userprofile__account__company_name__icontains=search_term)
            )

        return qs

    def get_context_data(self, **kwargs):
        context = super(AdminFlightWaitlistListView, self).get_context_data(**kwargs)

        search_term = self.request.GET.get('s')

        context.update({
            'search_term': search_term,
        })
        return context


class AdminFlightWaitlistDeleteView(StaffRequiredMixin, PermissionRequiredMixin, View):
    """
    Admin deletes waitlist entry via pk
    """

    permission_required = 'accounts.can_book_members'
    template_name = 'reservations/admin/waitlist.html'
    success_url = reverse_lazy('admin_list_waitlist')

    def get(self, request, *args, **kwargs):
        """
        Handle GET requests.  Gets waitlist pk and deletes it
        """
        waitlist_pk = self.kwargs.get('pk', None)
        if waitlist_pk:
            waitlist = get_object_or_404(FlightWaitlist, id=waitlist_pk)
            waitlist.status = FlightWaitlist.STATUS_CANCELLED
            waitlist.save()
            messages.info(request, 'Wishlist %s has been deleted.' % waitlist_pk)
            pass

        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse_lazy('admin_list_waitlist')


class AdminBookFromWaitlistView(StaffRequiredMixin, AdminReservationMixin, PermissionRequiredMixin, DetailView):
    """
    Displays basic flight and user information to initiate moving a passenger from the waitlist
    to a reservation
    """

    permission_required = 'accounts.can_book_members'
    template_name = 'reservations/admin/book_from_waitlist.html'
    model = FlightWaitlist

    def get(self, request, *args, **kwargs):
        """
        Handle GET requests.  Sets up reservation in the session from FlightWaitlist object
        """
        self.clear_all()
        return super(AdminBookFromWaitlistView, self).get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        """
        Handles POST requests, instantiating a form instance with the passed
        POST variables and then checked for validity.
        """

        self.object = self.get_object()
        flight = self.object.flight
        self.set_companion_count(self.object.passenger_count)
        if self.object.passenger_count + 1 > flight.seats_available:
            messages.error(request, "The number of seats for this reservation exceeds the seats available on the requested flight #%d." % flight.pk)
            return redirect('admin_list_waitlist')
        else:

            # handling restrictions on Flight Reservations for this flight and member
            if not flight.check_account_restriction(self.object.userprofile):
                messages.error(self.request, "There was an account restriction for %s on this flight. Please select a different member." % self.object.user.account)
                return redirect('admin_list_waitlist')

            # rise-356 handle people with active noshow restrictions
            if self.object.userprofile:
                noshow = self.object.userprofile.active_noshow_restriction()
                if noshow:
                    msg = AutomatedMessage.objects.filter(message_key=AutomatedMessage.NO_SHOW_RESTRICTION_ADMIN).first()
                    if msg:
                        msg_txt = msg.message_box_text.replace("[[end_date]]", noshow.end_date.strftime("%m-%d-%Y"))
                        messages.error(self.request, msg_txt)
                    else:
                        messages.error(self.request, "This person is restricted from all RISE activity until %s due to excessive no-shows." % noshow.end_date)
                    return redirect('admin_list_waitlist')

            if not flight.check_vip(self.object.userprofile):
                messages.error(self.request, "There was a VIP restriction on this flight, and %s is not a VIP account. Please select a different member." % self.object.user.account)
                return redirect('admin_list_waitlist')

            if not flight.check_founder(self.object.userprofile):
                messages.error(self.request, "There was a Founder restriction on this flight, and %s is not a Founder account. Please select a different member." % self.object.user.account)
                return redirect('admin_list_waitlist')

            if not flight.check_user_permissions(self.object.userprofile, self.object.passenger_count):
                messages.error(self.request, "There was a permission restriction for %s on this flight. Please select a different member." % self.object.user.get_full_name())
                return redirect('admin_list_waitlist')

            if not flight.check_plan_restrictions(self.object.userprofile, self.object.passenger_count):
                messages.error(self.request, "There was a plan restriction for %s on this flight. Please select a different member." % self.object.user.get_full_name())
                return redirect('admin_list_waitlist')

            if not flight.check_plan_seat_restrictions(self.object.user, (1 + self.object.passenger_count)):
                messages.error(self.request, "There was a seat restriction for %s's plan on this flight. Please select a different member." % self.object.user.get_full_name())
                return redirect('admin_list_waitlist')

            if flight.is_booked_by_user(self.object.userprofile):
                messages.error(self.request, "This flight already has a reservation for %s. Please select a different member." % self.object.user.get_full_name())
                return redirect('admin_list_waitlist')

            flight_reservation = flight.reserve_flight(request.user, self.object.userprofile, None, companion_count=self.object.passenger_count)

        if flight_reservation is not None:
            self.set_reservation(flight_reservation.reservation)
            self.set_booking_user(self.object.user)
            self.set_booking_userprofile(self.object.userprofile)
            self.set_flight_waitlist(self.object)

            if flight_reservation.passenger_count > 1:
                return redirect('admin_book_companions', pk=flight_reservation.pk)

            return redirect('admin_book_confirm')

        messages.error(request, 'There was an error booking the requested flight #%d. Please try again or choose another flight.' % flight.pk)
        return redirect('admin_list_waitlist')


class AdminBookConfirmationView(StaffRequiredMixin, AdminReservationMixin, PermissionRequiredMixin, TemplateView):
    """
    A view which displays the confirmed reservation when moving a passenger from the waitlist
    to a reservation
    """
    permission_required = 'accounts.can_book_members'
    reservation_required = True
    template_name = 'reservations/book/confirmation.html'

    def get_context_data(self, **kwargs):
        context = super(AdminBookConfirmationView, self).get_context_data(**kwargs)

        context.update({
            'reservation': self.reservation,
        })

        self.clear_reservation()
        self.clear_companion_count()
        self.clear_booking_user()
        self.clear_booking_userprofile()
        return context

    def get(self, *args, **kwargs):
        super(AdminBookConfirmationView, self).get(*args, **kwargs)

        # move this somewhere more central?
        if self.flight_waitlist:
            flight = self.flight_waitlist.flight
            self.flight_waitlist.status = FlightWaitlist.STATUS_RESERVED
            self.flight_waitlist.save()
            self.clear_flight_waitlist()
            return redirect('admin_flight_detail', pk=flight.pk)

        return redirect('admin_dashboard')


class AdminConfirmReservationView(StaffRequiredMixin, PermissionRequiredMixin, AdminReservationMixin, View):
    """
    A view to reserve a flight and redirect to confirm view when moving a passenger from the waitlist
    to a reservation
    """
    permission_required = 'accounts.can_book_members'
    reservation_required = True

    def get(self, request, *args, **kwargs):
        form = BookWithoutPaymentForm(request.GET)

        # if payment is required, check to make sure
        # form will always be valid, it's one field which is not required, just need the data cleaned
        form.is_valid()
        force_booking = form.cleaned_data.get('force_booking', False)
        if self.reservation.requires_payment() and self.reservation.charge is None and not force_booking:
            messages.error(self.request, 'Please provide payment information.')
            return redirect('admin_book_confirm')
        self.reservation.reserve()
        return redirect('admin_book_confirmed')


class AdminBookConfirmView(StaffRequiredMixin, PermissionRequiredMixin, AdminReservationMixin, FormView):
    """
    A view to confirm your a reservation or initiate additional billing when moving a passenger from the waitlist
    to a reservation
    """
    permission_required = 'accounts.can_book_members'
    reservation_required = True
    template_name = 'reservations/admin/book_confirm.html'
    form_class = SimplePaymentForm
    model = FlightWaitlist
    success_url = reverse_lazy('admin_book_reserve')

    def get_context_data(self, **kwargs):
        context = super(AdminBookConfirmView, self).get_context_data(**kwargs)
        account = self.booking_userprofile.account
        bill_pay_methods = BillingPaymentMethod.objects.filter(account=account).all()
        cards = Card.objects.filter(account=account).all()
        bankaccounts = BankAccount.objects.filter(account=account,verified=True).all()
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
        if self.booking_userprofile.account.has_braintree():
            client_token = braintree.ClientToken.generate({'customer_id': self.booking_userprofile.account.braintree_customer_id})
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
        user = self.booking_user
        userprofile = self.booking_userprofile
        reservation = self.reservation

        # if this reservation requires a payment
        if reservation.requires_payment():
             # get the stripe amount to charge
            amount = reservation.total_amount()
            payment_method = self.request.POST.get('payment_method')
            payment_method_nonce = form.cleaned_data.get('payment_method_nonce')
            # if no new card has been added or there is no existing card or bank account show error
            if not payment_method_nonce and payment_method is None:
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
                return super(AdminBookConfirmView, self).form_valid(form)
            # The user added a new credit card for payment.
            elif payment_method_nonce:
                #check if the user has an existing brain tree customer id and no credit card on his account
                # The new credit card is stored in the user account
                try:
                    nickname = form.cleaned_data.get('nickname')
                    card = paymentMethodUtil.createCreditCard(payment_method_nonce, False, userprofile.account.id, nickname)
                except paymentMethodUtil.CardException as e:
                    for error in e.message:
                        form.add_error(None,error)
                    return self.form_invalid(form)
                if userprofile.account.payment_method is None:
                    userprofile.account.payment_method = Account.PAYMENT_CREDIT_CARD
                    userprofile.account.save()
                description = 'Charge for reservation %s' % (reservation.pk,)
                charge = card.charge(amount, description, user)
                #if there is an existing credit card but wants to use a different card for the payment
                reservation.charge = charge
                reservation.save()
                return super(AdminBookConfirmView, self).form_valid(form)
            messages.error(self.request, 'Please provide payment information.')
            return self.form_invalid(form)

        return super(AdminBookConfirmView, self).form_valid(form)


class AdminCancelBookingView(StaffRequiredMixin, PermissionRequiredMixin, AdminReservationMixin, View):
    """
    A view to cancel the reservation during booking
    """
    permission_required = 'accounts.can_book_members'

    def get(self, request, *args, **kwargs):
        if self.reservation is not None:
            self.reservation.cancel()
        self.clear_all()

        return redirect('admin_list_waitlist')


class AdminCompanionSelectionView(StaffRequiredMixin, PermissionRequiredMixin, AdminReservationMixin, SingleObjectMixin, FormView):
    """
    A view to select which companions are also on the flight.
    """

    permission_required = 'accounts.can_book_members'
    template_name = 'reservations/admin/companions.html'
    reservation_required = True
    form_class = CompanionSelectionForm
    model = FlightReservation
    context_object_name = 'flight_reservation'

    def get_initial(self):
        initial = super(AdminCompanionSelectionView, self).get_initial()

        initial.update({
            'companions': [c.user for c in self.get_object().get_companions()],
        })

        return initial

    def get_form_kwargs(self):
        kwargs = super(AdminCompanionSelectionView, self).get_form_kwargs()

        kwargs.update({
            'account': self.booking_userprofile.account,
            'count': self.companion_count,
        })

        return kwargs

    def form_valid(self, form):
        companions = form.cleaned_data.get('companions')
        flight_reservation = self.get_object()
        flight_reservation.clear_companions()
        for companion in companions:
            flight_reservation.add_passenger(companion, companion=True)
        return redirect('admin_book_confirm')

    def get_context_data(self, **kwargs):
        self.object = self.get_object()
        context = super(AdminCompanionSelectionView, self).get_context_data(**kwargs)

        return context


class CheckInPassenger(StaffRequiredMixin, PermissionRequiredMixin, View):
    """
    Ajax view to check in passenger on a flight
    """

    permission_required = 'accounts.can_edit_members'

    def post(self, request, *args, **kwargs):
        passenger_pk = self.kwargs.get('pk', None)
        check_in = request.POST.get('check_in', None)
        if passenger_pk and check_in:
            passenger = get_object_or_404(Passenger, pk=passenger_pk)
            passenger.checked_in = True
            passenger.save()
            json_response = {'success': 'True'}
        elif passenger_pk and not check_in:
            passenger = get_object_or_404(Passenger, pk=passenger_pk)
            passenger.checked_in = False
            passenger.save()
            json_response = {'success': 'True'}
        else:
            json_response = {'error': "There was an error updating the Passenger #%s." % passenger_pk}

        return HttpResponse(json.dumps(json_response),
            content_type='application/json')


class ExportReservationsView(StaffRequiredMixin, PermissionRequiredMixin, View):
    """
    A view to export accounts to CSV
    """

    permission_required = 'accounts.can_view_members'

    def get(self, request, *args, **kwargs):
        today = arrow.now()
        weekday = today.isoweekday()
        if weekday < 7:
            weekday = weekday + 7
        start_date=today.datetime-timedelta(days=weekday)
        start_date_sunday = datetime(start_date.year,start_date.month,start_date.day, 0, 0, 0)
        flight_reservations = FlightReservation.objects.filter(flight__departure__gte=start_date).all().select_related('flight', 'flight__plane', 'reservation', 'reservation__account')
        date_format = 'YYYY-MM-DD HH:mm:ss ZZ'

        # Create the HttpResponse object with the appropriate CSV header.
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="reservations.csv"'

        writer = unicodecsv.writer(response)
        writer.writerow(['Account ID', 'Account Name', 'Status', 'Flight ID', 'Flight Number', 'Flight Status', 'Plane', 'Total Seats', 'Seats Available', 'Seats Reserved', 'Flight Departure', 'Flight Origin',
            'Flight Destination', 'Passenger Count', 'Passengers', 'Pass Count', 'Complimentary Pass Count', 'Companion Pass Count',
            'Complimentary Companion Pass Count', 'Buy Pass Count', 'Buy Companion Pass Count', 'Cost', 'Created',
            'Created By', 'Booked Hours Prior to Departure'])

        for flight_reservation in flight_reservations:
            minutes_prior = (flight_reservation.flight.departure - flight_reservation.created).total_seconds() / 3600.0

            writer.writerow([
                str(flight_reservation.reservation.account.id),
                flight_reservation.reservation.account.account_name(),
                flight_reservation.get_status_display(),
                flight_reservation.flight.id,
                flight_reservation.flight.flight_number,
                flight_reservation.flight.get_status_display(),
                flight_reservation.flight.plane.registration if flight_reservation.flight.plane else '',
                flight_reservation.flight.seats_total,
                flight_reservation.flight.seats_available,
                flight_reservation.flight.seats_total - flight_reservation.flight.seats_available,
                arrow.get(flight_reservation.flight.departure).format(date_format),
                flight_reservation.flight.origin,
                flight_reservation.flight.destination,
                flight_reservation.passenger_count,
                ', '.join([passenger.get_full_name() for passenger in flight_reservation.all_passengers()]),
                flight_reservation.pass_count,
                flight_reservation.complimentary_pass_count,
                flight_reservation.companion_pass_count,
                flight_reservation.complimentary_companion_pass_count,
                flight_reservation.buy_pass_count,
                flight_reservation.buy_companion_pass_count,
                flight_reservation.cost,
                arrow.get(flight_reservation.created).format(date_format),
                flight_reservation.created_by.get_full_name() if flight_reservation.created_by else '',
                minutes_prior,
            ])

        return response

class ExportReservationsViewByDate(StaffRequiredMixin, PermissionRequiredMixin, View):
    """
    A view to export accounts to CSV
    """

    permission_required = 'accounts.can_view_members'

    def get(self, request, *args, **kwargs):
        dt = datetime.strptime(settings.RESERVATION_EXPORT_DATE, "%d/%m/%y")
        flight_reservations = FlightReservation.objects.filter(flight__departure__gte=dt).all().select_related('flight', 'flight__plane', 'reservation', 'reservation__account')
        date_format = 'YYYY-MM-DD HH:mm:ss ZZ'

        # Create the HttpResponse object with the appropriate CSV header.
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="reservations.csv"'

        writer = unicodecsv.writer(response)
        writer.writerow(['Account ID', 'Account Name', 'Status', 'Flight ID', 'Flight Number', 'Flight Status', 'Plane', 'Total Seats', 'Seats Available', 'Seats Reserved', 'Flight Departure', 'Flight Origin',
            'Flight Destination', 'Passenger Count', 'Passengers', 'Pass Count', 'Complimentary Pass Count', 'Companion Pass Count',
            'Complimentary Companion Pass Count', 'Buy Pass Count', 'Buy Companion Pass Count', 'Cost', 'Created',
            'Created By', 'Booked Hours Prior to Departure'])

        for flight_reservation in flight_reservations:
            minutes_prior = (flight_reservation.flight.departure - flight_reservation.created).total_seconds() / 3600.0

            writer.writerow([
                str(flight_reservation.reservation.account.id),
                flight_reservation.reservation.account.account_name(),
                flight_reservation.get_status_display(),
                flight_reservation.flight.id,
                flight_reservation.flight.flight_number,
                flight_reservation.flight.get_status_display(),
                flight_reservation.flight.plane.registration if flight_reservation.flight.plane else '',
                flight_reservation.flight.seats_total,
                flight_reservation.flight.seats_available,
                flight_reservation.flight.seats_total - flight_reservation.flight.seats_available,
                arrow.get(flight_reservation.flight.departure).format(date_format),
                flight_reservation.flight.origin,
                flight_reservation.flight.destination,
                flight_reservation.passenger_count,
                ', '.join([passenger.get_full_name() for passenger in flight_reservation.all_passengers()]),
                flight_reservation.pass_count,
                flight_reservation.complimentary_pass_count,
                flight_reservation.companion_pass_count,
                flight_reservation.complimentary_companion_pass_count,
                flight_reservation.buy_pass_count,
                flight_reservation.buy_companion_pass_count,
                flight_reservation.cost,
                arrow.get(flight_reservation.created).format(date_format),
                flight_reservation.created_by.get_full_name() if flight_reservation.created_by else '',
                minutes_prior,
            ])

        return response


class ExportWaitListView(StaffRequiredMixin, PermissionRequiredMixin, View):
    """
    A view to export accounts to CSV
    """

    permission_required = 'accounts.can_view_members'

    def get(self, request, *args, **kwargs):
        waitlists = FlightWaitlist.objects.all().select_related('user', 'user__account', 'flight')

        date_format = 'YYYY-MM-DD HH:mm:ss ZZ'

        # Create the HttpResponse object with the appropriate CSV header.
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="waitlist.csv"'

        writer = unicodecsv.writer(response)
        writer.writerow(['Account ID', 'Account Name', 'Flight ID', 'Flight Number', 'Flight Departure', 'Flight Origin',
            'Flight Destination', 'Passenger Count', 'Created', 'Status'])

        for waitlist in waitlists:
            writer.writerow([
                waitlist.user.account.id,
                waitlist.user.account.account_name(),
                waitlist.flight.id,
                waitlist.flight.flight_number,
                arrow.get(waitlist.flight.departure).format(date_format),
                waitlist.flight.origin,
                waitlist.flight.destination,
                waitlist.passenger_count,
                arrow.get(waitlist.created).format(date_format),
                waitlist.get_status_display(),
            ])

        return response
