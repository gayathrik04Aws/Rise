from django.views.generic import DetailView, FormView, UpdateView, TemplateView, ListView, DeleteView, CreateView, View
from django.shortcuts import redirect
from django.db.models import Sum, F, Q
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse_lazy
from django.http import Http404, HttpResponse
from django.utils.functional import cached_property
from django.template.loader import render_to_string
from django.shortcuts import get_object_or_404
from django.core.mail import send_mail
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
import datetime
from dateutil.relativedelta import relativedelta
from htmlmailer.mailer import send_html_email
import arrow
import json
import braintree
import stripe
from billing import paymentMethodUtil
from accounts.models import User, UserProfile, Address, FoodOption, Invite, Account, BillingPaymentMethod
from billing.models import Card, Charge, BankAccount, Subscription
from flights.models import Flight, Airport
from reservations.models import FlightReservation, Passenger, Reservation, FlightWaitlist
from accounts.mixins import LoginRequiredMixin, PermissionRequiredMixin
from accounts.forms import ChangePlanForm
from announcements.models import Announcement
from anywhere.models import AnywhereFlightSet, AnywhereFlightRequest
from .forms import ProfileForm, AvatarForm, BillingUpdateForm, SendInvitationForm, NotificationsForm, CompanionForm
from .forms import AddEditMemberForm, FilterMemberForm, FilterReservationsForm, ReservationEmailForm, BankAccountForm, BankAccountVerifyForm


stripe.api_key = settings.STRIPE_API_KEY


class DashboardView(LoginRequiredMixin, TemplateView):
    """
    A user's dashboard view
    """

    template_name = 'account_profile/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super(DashboardView, self).get_context_data(**kwargs)

        user = self.request.user
        userprofile = user.userprofile
        flights_completed = Passenger.objects.filter(userprofile=userprofile, flight_reservation__status=FlightReservation.STATUS_COMPLETE).count()
        hours_saved = flights_completed * 2
        minutes = Passenger.objects.filter(userprofile=userprofile, flight_reservation__status=FlightReservation.STATUS_COMPLETE).only('flight_reservation__flight__duration').aggregate(minutes=Sum('flight_reservation__flight__duration')).get('minutes')
        if minutes is None:
            minutes = 0
        hours = minutes / 60

        now = arrow.now().datetime
        upcoming_passengers = Passenger.objects.filter(userprofile=userprofile, flight_reservation__flight__status__in=(Flight.STATUS_ON_TIME, Flight.STATUS_DELAYED), flight_reservation__flight__departure__gte=now, flight_reservation__status__in=(FlightReservation.STATUS_RESERVED, FlightReservation.STATUS_CHECKED_IN)).select_related().order_by('flight_reservation__flight__departure')[:5]
        upcoming_flight_reservations = [passenger.flight_reservation for passenger in upcoming_passengers]

        if not user.account or user.account.is_corporate():
            members = UserProfile.objects.filter(user__is_active=True, account=user.account)[:10]
        else:
            members = user.account.get_companion_profiles()[:10]

        #dashboard now includes a page of available RiseAnywhere flights as well
        flightsets = AnywhereFlightSet.get_available_flightsets()
        paginator = Paginator(flightsets, settings.DASHBOARD_ANYWHERE_LIST_PAGESIZE)

        now = arrow.now().datetime
        date_kwargs = {
             '{0}__{1}'.format('flight__departure', 'gte'): now,
        }

        user = self.request.user
        statuses = (FlightReservation.STATUS_ANYWHERE_PENDING)
        id_list = Passenger.objects.filter(userprofile=userprofile, flight_reservation__status__in=statuses).values_list('flight_reservation', flat=True)
        #anywhere_reservations = FlightReservation.objects.filter(status__in=statuses, id__in=id_list, **date_kwargs).order_by('flight__departure').select_related()
        reservation_queryset = FlightReservation.objects.filter(status__in=statuses, id__in=id_list, **date_kwargs).order_by('flight__departure')
        pending_flightids = reservation_queryset.values_list('flight_id', flat=True)
        flightsets = AnywhereFlightSet.objects.filter((Q(leg1_id__in=pending_flightids) & Q(leg2_id__in=pending_flightids) & Q(anywhere_request__is_round_trip=1)) | (Q(leg1_id__in=pending_flightids) & Q(anywhere_request__is_round_trip=0)) ).all()

        anywhere_request_date_kwargs = {
             '{0}__{1}'.format('depart_date', 'gte'): now,
        }
        anywhere_requests = AnywhereFlightRequest.objects.filter(created_by_id=user.id, status=AnywhereFlightRequest.STATUS_PENDING,**anywhere_request_date_kwargs).all()

        waitlist = FlightWaitlist.objects.filter(userprofile=userprofile, status=FlightWaitlist.STATUS_WAITING, **date_kwargs).all()


        context.update({
            'airports': Airport.objects.all(),
            'flights_completed': flights_completed,
            'hours': hours,
            'hours_saved': hours_saved,
            'upcoming_flight_reservations': upcoming_flight_reservations,
            'members': members,
            'announcements': Announcement.objects.all()[:3],
            'flightset_list': paginator.page(1),
            'hide_flightset_pager': True,
            'pending_reservations': flightsets,
            'unapproved_requests': anywhere_requests,
            'waitlist': waitlist
        })

        return context

class ReservationsView(LoginRequiredMixin, TemplateView):
    """
    A view to display all of a user's reservations
    """

    def get_template_names(self):
        """
        Returns a list of template names to be used for the request. Must return
        a list. May not be called if render_to_response is overridden.
        """
        user = self.request.user
        if user.account.is_corporate() and user.has_perm('accounts.can_book_team'):
            return ['account_profile/reservation_list_team.html']

        return ['account_profile/reservation_list.html']

    def get_context_data(self, **kwargs):
        context = super(ReservationsView, self).get_context_data(**kwargs)

        status = self.kwargs.get('status')
        now = arrow.now().datetime

        if status == 'upcoming':
            statuses = (FlightReservation.STATUS_RESERVED, FlightReservation.STATUS_CHECKED_IN,
                FlightReservation.STATUS_CANCELLED)
            date_kwargs = {
                '{0}__{1}'.format('flight__departure', 'gte'): now,
            }
        elif status == 'complete':
            statuses = (FlightReservation.STATUS_COMPLETE)
            date_kwargs = {
                '{0}__{1}'.format('flight__departure', 'lte'): now,
            }
        else:
            statuses = (FlightReservation.STATUS_RESERVED, FlightReservation.STATUS_CHECKED_IN,
                        FlightReservation.STATUS_COMPLETE, FlightReservation.STATUS_CANCELLED)
            date_kwargs = {}

        selected = status
        user = self.request.user
        userprofile = user.userprofile

        # if the user can book for the team, show all account bookings
        if user.account and (user.account.is_corporate() and user.has_perm('accounts.can_book_team')) or (user.has_perm('accounts.can_manage_companions')):
            flight_reservations = FlightReservation.objects.filter(status__in=statuses, reservation__account=user.account, **date_kwargs).order_by('flight__departure').select_related()
        else:
            id_list = Passenger.objects.filter(userprofile=userprofile, flight_reservation__status__in=statuses).values_list('flight_reservation', flat=True)
            flight_reservations = FlightReservation.objects.filter(status__in=statuses, id__in=id_list, **date_kwargs).order_by('flight__departure').select_related()

        # retrofitting for GET sorting, filtering and search
        sort_param = self.request.GET.get('sort', None)
        sort_on = None
        if sort_param == 'a-z':
            sort_on = 'passenger__last_name'
            selected = 'alpha-last-name'
        elif sort_param == 'z-a':
            sort_on = '-passenger__last_name'
            selected = 'reverse-alpha-last-name'

        type_param = self.request.GET.get('type', None)
        flight_type = None
        if type_param == 'fun':
            flight_type = Flight.TYPE_FUN
            selected = 'fun'
        elif type_param == 'promo':
            flight_type = Flight.TYPE_PROMOTION
            selected = 'promotional'

        search_param = self.request.GET.get('s', None)
        search_on = None
        if search_param:
            search_on = search_param

        # TODO: the following should probably start over with separate queries especially if we end up paginating the
        # original results

        if sort_on:
            flight_reservations = flight_reservations.order_by(sort_on)
        elif flight_type:
            flight_reservations = flight_reservations.filter(~Q(status=FlightReservation.STATUS_CANCELLED) | Q(flight__departure__gte=now), flight__flight_type=flight_type)
        if search_on:
            # TODO: Expand search to an indexing implementation like Elastic Search
            flight_reservations = flight_reservations.filter(
                Q(passenger__first_name__icontains=search_on) |
                Q(passenger__last_name__icontains=search_on) |
                Q(passenger__email__icontains=search_on) |
                Q(flight__flight_number__icontains=search_on) |
                Q(flight__origin__name__icontains=search_on) |
                Q(flight__origin__code__icontains=search_on) |
                Q(flight__destination__name__icontains=search_on) |
                Q(flight__destination__code__icontains=search_on)
            )

        if status != 'complete':
            if user.account and (user.account.is_corporate() and user.has_perm('accounts.can_book_team')) or (user.has_perm('accounts.can_manage_companions')):
                waitlist = FlightWaitlist.objects.filter(user__account=user.account, status=FlightWaitlist.STATUS_WAITING, **date_kwargs).all()
            else:
                waitlist = FlightWaitlist.objects.filter(userprofile=userprofile, status=FlightWaitlist.STATUS_WAITING, **date_kwargs).all()
            #also include pending anywhere flights and unapproved requests
            statuses = (FlightReservation.STATUS_ANYWHERE_PENDING)
            departdate_kwargs = {
                '{0}__{1}'.format('depart_date', 'gte'): now,
            }
            if user.account and user.account.is_corporate() and user.has_perm('accounts.can_book_team'):
                id_list = User.objects.filter(account_id=user.account.id).values_list('id',flat=True)
                anywhere_reservations = FlightReservation.objects.filter(status__in=statuses, reservation__account_id=user.account.id, **date_kwargs).order_by('flight__departure').select_related()
                anywhere_requests = AnywhereFlightRequest.objects.filter(created_by_id__in=id_list, status=AnywhereFlightRequest.STATUS_PENDING,**departdate_kwargs).all()
            else:
                id_list = Passenger.objects.filter(userprofile=userprofile, flight_reservation__status__in=statuses).values_list('flight_reservation', flat=True)
                anywhere_reservations = FlightReservation.objects.filter(status__in=statuses, id__in=id_list, **date_kwargs).order_by('flight__departure').select_related()
                anywhere_requests = AnywhereFlightRequest.objects.filter(created_by_id=user.id, status=AnywhereFlightRequest.STATUS_PENDING,**departdate_kwargs).all()

        else:
            anywhere_reservations = None
            anywhere_requests = None
            waitlist = None

        context.update({
            'flight_reservations': flight_reservations,
            'pending_reservations': anywhere_reservations,
            'unapproved_requests': anywhere_requests,
            'filter_reservations_form': FilterReservationsForm(account=user.account, initial={'reservation_filters': '%s-flights' % selected}),
            'filter_member_form': FilterMemberForm(account=user.account, initial={'member_filters': ''}),
            'status': status,
            'waitlist': waitlist
        })

        return context


class ReservationDetailView(LoginRequiredMixin, TemplateView):
    """
    A view to see the details of a flight reservation
    """

    template_name = 'account_profile/reservation_detail.html'

    def get_context_data(self, **kwargs):
        context = super(ReservationDetailView, self).get_context_data(**kwargs)
        pk = self.kwargs.get('pk')
        user = self.request.user
        flight_reservation = None
        # if the user can book for the whole account
        if user.account.is_corporate() and user.has_perm('accounts.can_book_team'):
            flight_reservation = next(iter(FlightReservation.objects.filter(pk=pk, reservation__account=user.account).select_related()), None)
        # otherwise the user will need to be a passenger on the flight
        else:
            passenger = next(iter(Passenger.objects.filter(userprofile=user.userprofile, flight_reservation__pk=pk).select_related()), None)
            if passenger is not None:
                flight_reservation = passenger.flight_reservation

        if flight_reservation is None:
            raise Http404

        context.update({
            'flight_reservation': flight_reservation,
            'flight_messages': flight_reservation.flight.flight_flight_messages.exclude(internal=True),
        })

        return context


class FlightReservationiCalView(LoginRequiredMixin, View):
    """
    This view returns an iCal attachement for a reservation
    """

    def get(self, request, *args, **kwargs):
        try:
            flight_reservation = FlightReservation.objects.select_related().get(reservation__account=self.request.user.account, pk=self.kwargs.get('pk'))
        except FlightReservation.DoesNotExist:
            raise Http404

        ical = flight_reservation.ical()

        response = HttpResponse(ical.to_ical(), content_type='text/calendar')
        response['Content-Disposition'] = 'attachment; filename="reservation.ics"'
        return response


class ReservationiCalView(LoginRequiredMixin, View):
    """
    This view returns an iCal attachement for a reservation
    """

    def get(self, request, *args, **kwargs):
        try:
            reservation = Reservation.objects.select_related().get(account=self.request.user.account, pk=self.kwargs.get('pk'))
        except Reservation.DoesNotExist:
            raise Http404

        ical = reservation.ical()

        response = HttpResponse(ical.to_ical(), content_type='text/calendar')
        response['Content-Disposition'] = 'attachment; filename="reservation.ics"'
        return response


class ReservationEmailView(LoginRequiredMixin, FormView):
    """
    This view allows a user to send a copy of a reservation to one or more emails
    """

    template_name = 'account_profile/reservation_email_form.html'
    form_class = ReservationEmailForm

    @cached_property
    def reservation(self):
        try:
            reservation = Reservation.objects.select_related().get(account=self.request.user.account, pk=self.kwargs.get('pk'))
            return reservation
        except Reservation.DoesNotExist:
            raise Http404

    def get_context_data(self, **kwargs):
        context = super(ReservationEmailView, self).get_context_data(**kwargs)

        context.update({'reservation': self.reservation, })

        return context

    def form_valid(self, form):
        emails = form.cleaned_data.get('emails')

        reservation = self.reservation

        reservation.send_reservation_email(to=emails)

        messages.info(self.request, 'Emails have been sent.')

        return redirect('dashboard')


class ProfileView(LoginRequiredMixin, DetailView):
    """
    View the Basic Information page
    """

    template_name = 'account_profile/profile.html'
    context_object_name = 'account'

    def get_object(self, queryset=None):
        if self.request.user.is_authenticated():
            user = self.request.user
            account = user.account
            if not account:
                raise Http404
        else:
            raise Http404

        return account


class EditProfileView(LoginRequiredMixin, FormView):
    """
    Edit Profile informtaion
    """

    template_name = 'account_profile/edit_profile.html'
    form_class = ProfileForm
    success_url = reverse_lazy('profile')

    def get_initial(self):
        initial = super(EditProfileView, self).get_initial()

        user = self.request.user

        initial.update({
            'avatar': user.avatar_url,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': user.email,
        })

        try:
            account = user.account
            initial.update({'company_name': account.company_name})
        except:
            pass

        try:
            user_profile = user.user_profile
            initial.update({
                'phone': user_profile.phone,
                'mobile_phone': user_profile.mobile_phone,
                'date_of_birth': user_profile.date_of_birth,
                'weight': user_profile.weight,
                'food_options': user_profile.food_options.all(),
                'allergies': user_profile.allergies,
                'origin_airport': user_profile.origin_airport,
            })

            address = user_profile.shipping_address

            if address is not None:
                initial.update({
                    'ship_street_1': address.street_1,
                    'ship_street_2': address.street_2,
                    'ship_city': address.city,
                    'ship_state': address.state,
                    'ship_postal_code': address.postal_code,
                })
        except:
            pass

        return initial

    def get_form_kwargs(self):
        kwargs = super(EditProfileView, self).get_form_kwargs()

        kwargs.update({
            'user': self.request.user,
        })

        return kwargs

    def form_valid(self, form):

        user = self.request.user

        user.first_name = form.cleaned_data.get('first_name')
        user.last_name = form.cleaned_data.get('last_name')
        user.email = form.cleaned_data.get('email')
        user.save()

        user.account.company_name = form.cleaned_data.get('company_name')
        user.account.save()

        try:
            user_profile = user.user_profile
        except:
            user_profile = UserProfile(user=user)

        user_profile.phone = form.cleaned_data.get('phone')
        user_profile.mobile_phone = form.cleaned_data.get('mobile_phone')
        user_profile.date_of_birth = form.cleaned_data.get('date_of_birth')
        user_profile.weight = form.cleaned_data.get('weight').strip()
        user_profile.origin_airport = form.cleaned_data.get('origin_airport')
        user_profile.allergies = form.cleaned_data.get('allergies').strip()

        address = user_profile.shipping_address
        if address is None:
            address = Address()

        address.street_1 = form.cleaned_data.get('ship_street_1').strip()
        address.street_2 = form.cleaned_data.get('ship_street_2').strip()
        address.city = form.cleaned_data.get('ship_city').strip()
        address.state = form.cleaned_data.get('ship_state').strip()
        address.postal_code = form.cleaned_data.get('ship_postal_code').strip()
        address.save()

        user_profile.shipping_address = address
        user_profile.save()

        food_options = form.cleaned_data.get('food_options')

        # update user profile's food_options set from food_options list of id's
        old_food_options = user_profile.food_options.all()
        update_food_options = FoodOption.objects.filter(id__in=food_options)
        delete_food_options = set(old_food_options) - set(update_food_options)
        new_food_options = set(update_food_options) - set(old_food_options)

        for option in delete_food_options:
            user_profile.food_options.remove(option)

        for option in new_food_options:
            user_profile.food_options.add(option)

        return super(EditProfileView, self).form_valid(form)


class UpdateAvatarView(LoginRequiredMixin, UpdateView):
    """
    Update Avatar file
    """

    template_name = 'account_profile/update_avatar.html'
    model = User
    form_class = AvatarForm
    success_url = reverse_lazy('profile')

    def get_initial(self):
        initial = super(UpdateAvatarView, self).get_initial()

        user = self.request.user

        if user:
            initial.update({
                'avatar': user.avatar_url
            })

        return initial

    def get_object(self, queryset=None):
        return self.request.user

    def form_valid(self, form):
        self.object = form.save()
        return HttpResponse(json.dumps({'success': 'true'}), content_type="application/json")

    def form_invalid(self, form):
        return HttpResponse(json.dumps({'error': 'There was an error updating your profile image.'}), content_type="application/json")


class PlanOptionsView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """
    A view to display plan options
    """

    permission_required = 'accounts.can_manage_plan'
    template_name = 'account_profile/plan_options.html'


class ChangePlanView(LoginRequiredMixin, PermissionRequiredMixin, FormView):
    """
    A view to allow an individual member to change their membership plan
    """

    permission_required = 'accounts.can_manage_plan'
    template_name = 'account_profile/change_plan.html'
    form_class = ChangePlanForm
    success_url = reverse_lazy('profile_plan')

    def get_initial(self):
        initial = super(ChangePlanView, self).get_initial()

        flight_pk = self.kwargs.get('pk', None)

        if flight_pk:
            flight = get_object_or_404(Flight, id=flight_pk)
            minimum_plan = flight.get_minimum_plan()
            if minimum_plan:
                member_plan = minimum_plan
            else:
                member_plan = self.request.user.account.plan
        else:
            member_plan = self.request.user.account.plan

        contract = self.request.user.account.contract

        initial.update({
            'member_plan': member_plan,
            'contract': contract
        })

        return initial

    def form_valid(self, form):
        flight_pk = self.kwargs.get('pk', None)
        new_plan = form.cleaned_data.get('member_plan')
        if 'contract' in form.changed_data:
            new_contract = form.cleaned_data.get('contract')
        else:
            new_contract = None
        try:
            current_plan = self.request.user.account.plan
        except:
            current_plan = 'None'

        self.request.user.account.change_plan(new_plan, force=True, contract=new_contract,user=self.request.user)

        subject = 'Account %s Plan Change' % self.request.user.account.account_name()
        message_body = "%s has changed the plan for Account %s from %s to %s." % (self.request.user.get_full_name(), self.request.user.account.account_name(), current_plan, new_plan)
        send_mail(subject, message_body, 'info@iflyrise.com', ['support@iflyrise.com'])

        if flight_pk and flight_pk.isdigit():
            return redirect('reserve_flight', flight_pk)
        else:
            return super(ChangePlanView, self).form_valid(form)


class UpgradePlanView(LoginRequiredMixin, PermissionRequiredMixin, View):

    permission_required = 'accounts.can_manage_plan'

    def get(self, request, *args, **kwargs):
        from billing.models import Plan
        current_plan = self.request.user.account.plan
        new_plan = Plan.objects.get(name=self.kwargs.get('plan'))
        self.request.user.account.change_plan(new_plan,user=self.request.user)

        subject = 'Account %s Plan Upgrade' % self.request.user.account.account_name()
        message_body = "%s has changed the plan for Account %s from %s to %s." % (self.request.user.get_full_name(), self.request.user.account.account_name(), current_plan, new_plan)
        send_mail(subject, message_body, 'info@iflyrise.com', ['support@iflyrise.com'])

        return redirect('book_from', new_plan.name.lower())


class BillingInfoView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """
    A view to display user's billing information
    """

    permission_required = 'accounts.can_manage_billing'
    template_name = 'account_profile/billing_info.html'

    def get_context_data(self, **kwargs):
        context = super(BillingInfoView, self).get_context_data(**kwargs)

        recent_charges = Charge.objects.filter(account=self.request.user.account).order_by('-created')[:5]

        context.update({
            'recent_charges': recent_charges,
        })

        return context


class PaymentMethodView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """
    A view to set the default payment method for an account
    """

    permission_required = 'accounts.can_manage_billing'

    def get(self, request, *args, **kwargs):
        billing_payment_method_id = self.kwargs.get('pk')
        account = request.user.account
        paymentMethodUtil.setDefaultPayment(billing_payment_method_id, account.id)
        return redirect('profile_billing')


class DeleteCreditCardView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """
    A view to delete a credit card from an account
    """

    permission_required = 'accounts.can_manage_billing'

    def get(self, request, *args, **kwargs):
        card_id = self.kwargs.get('pk')
        paymentMethodUtil.deleteCreditCard(card_id)
        return redirect('profile_billing')


class DeleteBankAccountView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """
    A view to delete a bank account from an account
    """

    permission_required = 'accounts.can_manage_billing'

    def get(self, request, *args, **kwargs):
        bank_id = self.kwargs.get('pk')
        paymentMethodUtil.deleteBankAccountView(bank_id, request.user.account.id)
        return redirect('profile_billing')


class UpdateCreditCardView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """
    A view to allow a user to update their credit card
    """

    permission_required = 'accounts.can_manage_billing'
    template_name = 'account_profile/edit_credit_card.html'
    form_class = BillingUpdateForm
    success_url = reverse_lazy('profile_billing')

    def get_object(self, queryset=None):
        return self.request.user.user_profile.billing_address

    @cached_property
    def account(self):
        return self.request.user.account

    def get_context_data(self, **kwargs):
        context = super(UpdateCreditCardView, self).get_context_data(**kwargs)

        if self.account.has_braintree():
            client_token = braintree.ClientToken.generate({'customer_id': self.account.braintree_customer_id})
        else:
            client_token = braintree.ClientToken.generate()

        context.update({
            'STRIPE_PUBLISHABLE_KEY': settings.STRIPE_PUBLISHABLE_KEY,
            'client_token': client_token,
        })

        return context

    def form_valid(self, form):
        payment_method_nonce = form.cleaned_data.get('payment_method_nonce')
        is_default = form.cleaned_data.get('is_default')
        nickname = form.cleaned_data.get('nickname')
        try:
            card = paymentMethodUtil.createCreditCard(payment_method_nonce, is_default, self.account.id, nickname)
        except paymentMethodUtil.CardException as e:
            for error in e.message:
                form.add_error(None,error)
            return self.form_invalid(form)
        account = self.account
        # if the onboarding fee has not been paid yet, and is ACH acccount
        onboarding_fee = account.get_onboarding_fee_total()
        if not account.onboarding_fee_paid and onboarding_fee > 0:
            if account.is_corporate():
                description = 'Fee for %d team members ($%d/member) + %s tax' % (account.member_count, settings.DEPOSIT_COST, settings.DEPOSIT_TAX_PERCENT)
            else:
                description = 'Member initation fee'

            if card is not None:
                try:
                    charge = card.charge(onboarding_fee, description, self.request.user)
                    charge.send_receipt_email(subtotal=account.get_onboarding_fee(), tax=account.get_onboarding_fee_tax(),
                                          tax_percentage=settings.DEPOSIT_TAX_PERCENT)
                    account.onboarding_fee_paid = True
                    account.save()
                except Exception as e:
                    messages.error(self.request, e.message)

        return super(UpdateCreditCardView, self).form_valid(form)


class BankAccountView(PermissionRequiredMixin, FormView):
    """
    A view to update an account's bank account
    """

    permission_required = 'accounts.can_manage_billing'
    form_class = BankAccountForm
    template_name = 'account_profile/bank_account_form.html'

    @cached_property
    def account(self):
        return self.request.user.account

    def get_context_data(self, **kwargs):
        context = super(BankAccountView, self).get_context_data(**kwargs)
        user = self.request.user
        if user is not None:
            if user.account is not None:
                if user.account.account_type == 'C':
                    account_holder_type = 'company'
                    account_holder_name = user.account.company_name
                else:
                    account_holder_type = 'individual'
                    account_holder_name = user.first_name + ' ' + user.last_name
            else:
                account_holder_type = 'individual'
                account_holder_name = user.first_name + ' ' + user.last_name

        bank_account = self.account.get_bank_account()
        if bank_account is not None:
            context.update({'routing_number': bank_account.routing_number})

        context.update({
            'STRIPE_PUBLISHABLE_KEY': settings.STRIPE_PUBLISHABLE_KEY,
            'account_holder_name': account_holder_name,
            'account_holder_type': account_holder_type,
        })

        return context

    def form_valid(self, form):
        token = form.cleaned_data.get('token')
        routing = form.cleaned_data.get('routing')
        last4 = form.cleaned_data.get('last4')
        try:
            paymentMethodUtil.createBankAccount(self.account.id, token, form.cleaned_data.get('nickname'), routing=routing, last4=last4)
        except paymentMethodUtil.CardException as e:
            for error in e.message:
                form.add_error(None,error)
            return self.form_invalid(form)
        return redirect('profile_billing')


class BankAccountVerifyView(PermissionRequiredMixin, FormView):
    """
    A view to update an account's bank account
    """

    permission_required = 'accounts.can_manage_billing'
    form_class = BankAccountVerifyForm
    template_name = 'account_profile/bank_account_verify_form.html'

    def form_valid(self, form):
        verify_1 = int(form.cleaned_data.get('verify_1') * 100)
        verify_2 = int(form.cleaned_data.get('verify_2') * 100)

        account = self.request.user.account
        stripe_customer = account.get_stripe_customer()
        bank_account = account.get_bank_account()
        # AMF Rise-149 This needs to pull the exact stripe acct by ID, not the default account, otherwise correct
        # accout won't get verified if there are multiple bank accounts registered for this customer with stripe.
        if bank_account is not None:
            stripe_bank_account = stripe_customer.bank_accounts.retrieve(bank_account.stripe_id)
        else:
            return self.form_invalid(form)

        if not stripe_bank_account.verified:
            try:
                stripe_bank_account = stripe_bank_account.verify(amounts=(verify_1, verify_2))
                bank_account.update_from_stripe_bank_account(stripe_bank_account)
                bank_account.save()
                messages.info(self.request, 'Bank account verified.')
            except Exception, e:
                form.add_error(None, e.message)
                return self.form_invalid(form)
        else:
            bank_account.verified = True
            bank_account.save()
            messages.info(self.request, 'Bank account verified.')

        if account.status == Account.STATUS_PENDING_ACH or account.status == Account.STATUS_PENDING:
            account.status = Account.STATUS_ACTIVE
            if account.contract:
                account.contract_start_date = datetime.datetime.now()
                account.contract_end_date = account.contract_start_date + relativedelta(months=account.contract.contract_length)
            account.save()

        # if no credit card on file, ensure payment method is set to ACH
        if account.get_credit_card() is None and not account.is_manual():
            account.payment_method = Account.PAYMENT_ACH
            account.save()

        # bill first subscription fee
        subscription = account.get_subscription()
        if subscription is None:
            subscription = Subscription.objects.create_subscription(account, created_by=self.request.user)

        # if the onboarding fee has not been paid yet, and is ACH acccount
        onboarding_fee = account.get_onboarding_fee_total()
        if not account.onboarding_fee_paid and onboarding_fee > 0 and account.is_ach():
            if account.is_corporate():
                description = 'Fee for %d team members ($%d/member) + %s tax' % (account.member_count, settings.DEPOSIT_COST, settings.DEPOSIT_TAX_PERCENT)
            else:
                description = 'Member initation fee'
            charge = account.charge(onboarding_fee, description, self.request.user)
            charge.send_receipt_email(subtotal=account.get_onboarding_fee(), tax=account.get_onboarding_fee_tax(),
                                      tax_percentage=settings.DEPOSIT_TAX_PERCENT)

            account.onboarding_fee_paid = True
            account.save()

        return redirect('profile_billing')


class ChargeListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """
    A view to show a user all of their charges
    """

    permission_required = 'accounts.can_manage_billing'
    template_name = 'account_profile/billing_history.html'

    def get_queryset(self):
        return Charge.objects.filter(account=self.request.user.account).order_by('-created')


class NotificationsView(LoginRequiredMixin, UpdateView):

    template_name = 'account_profile/notifications.html'
    form_class = NotificationsForm
    success_url = reverse_lazy('profile_notifications')

    def get_object(self, queryset=None):
        try:
            user_profile = self.request.user.user_profile
        except:
            user_profile = UserProfile.objects.create(user=self.request.user)
        return user_profile


class InvitationsView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """
    View the Basic Information page
    """

    permission_required = 'accounts.can_mange_invites'
    template_name = 'account_profile/invitations.html'

    def get_context_data(self, **kwargs):
        context = super(InvitationsView, self).get_context_data(**kwargs)
        account = self.request.user.account

        pending_invites = account.invite_set.filter(redeemed=False)
        redeemed_invites = account.invite_set.filter(redeemed=True)

        context.update({
            'pending_invites': pending_invites,
            'redeemed_invites': redeemed_invites
        })

        return context


class RequestInvitationsView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """
    Ask the site administrator for more invitations to send
    """

    permission_required = 'accounts.can_mange_invites'
    template_name = 'account_profile/request_invitations.html'

    def get(self, request, *args, **kwargs):
        first_name = request.user.first_name
        last_name = request.user.last_name
        email = request.user.email

        subject = 'Request from %s %s regarding additional invites' % (first_name, last_name)

        context = {
            'name': "%s %s" % (first_name, last_name),
            'subject': subject,
            'email': email,
        }

        text_content = render_to_string('emails/invitation_request.txt', context)

        send_mail(subject, text_content, email, ['Rise <members@iflyrise.com>'])

        messages.info(request, 'More invitations have been requested.')

        return redirect('profile_invitations')


class SendInvitationView(LoginRequiredMixin, PermissionRequiredMixin, FormView):
    """
    Send an invitation to a third party of the user's choice
    """

    permission_required = 'accounts.can_mange_invites'
    template_name = 'account_profile/send_invitation.html'
    form_class = SendInvitationForm
    success_url = reverse_lazy('profile_invitations')

    def form_valid(self, form):
        """
        If the form is valid, save the form to create an invite
        """
        first_name = form.cleaned_data.get('first_name')
        last_name = form.cleaned_data.get('last_name')
        email = form.cleaned_data.get('email').strip()

        invite = Invite.objects.create_digital_invite(self.request.user, email, origin_city=None, first_name=first_name, last_name=last_name, phone=None)

        # update the number of invites remaining
        Account.objects.filter(id=self.request.user.account_id).update(invites=F('invites') - 1)

        subject = 'You are invited to join Rise!'

        context = {
            'invite': invite,
        }

        send_html_email('emails/invitation_email', context, subject, settings.DEFAULT_FROM_EMAIL, [email])

        messages.info(self.request, 'Your invite has been sent!')

        return redirect(self.get_success_url())


class CompanionsView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """
    View the Companions page
    """
    permission_required = 'accounts.can_manage_companions'
    template_name = 'account_profile/companion_list.html'
    model = UserProfile

    def get_queryset(self):
        userids = User.objects.filter(groups__name='Companion', account__id=self.request.user.account_id, is_active=True).values_list("id", flat=True)
        return UserProfile.objects.filter(Q(user__id__in=userids) | (Q(user__isnull=True) & Q(account__id=self.request.user.account_id)))


class DeleteCompanionView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    """
    Allows the User to delete a companion
    """
    permission_required = 'accounts.can_manage_companions'
    template_name = 'account_profile/companion_confirm_delete.html'
    model = User
    context_object_name = 'companion'
    success_url = reverse_lazy('profile_companions')

    def get_queryset(self):
        """
        Ensure the user is a companion and on this account
        """
        return User.objects.filter(is_active=True, account__id=self.request.user.account_id, groups__name='Companion')


class AddCompanionView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """
    Add a companion
    """
    permission_required = 'accounts.can_manage_companions'
    template_name = 'account_profile/companion_add.html'
    form_class = CompanionForm
    model = UserProfile
    success_url = reverse_lazy('profile_companions')

    def get_initial(self):
        """
        Returns the initial data to use for forms on this view.
        """
        initial = super(AddCompanionView, self).get_initial()
        account = self.request.user.account
        initial['account'] = account

        return initial

    def get_form_kwargs(self):
        kwargs = super(AddCompanionView, self).get_form_kwargs()

        kwargs.update({
            'user': None,
        })

        return kwargs

    def form_valid(self, form):
        companion_group = Group.objects.get(name='Companion')

        companionprofile = form.save()

        # companion.account = self.request.user.account
        # companion.save()

        if companionprofile.user:
            companionprofile.user.groups.add(companion_group)

        return super(AddCompanionView, self).form_valid(form)


class EditCompanionView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """
    Edit Companion
    """
    permission_required = 'accounts.can_manage_companions'
    template_name = 'account_profile/companion_edit.html'
    form_class = CompanionForm
    model = UserProfile
    context_object_name = 'companion'
    success_url = reverse_lazy('profile_companions')

    def get_queryset(self):
        """
        Ensure the user is on this account
        """
        return UserProfile.objects.filter(account__id=self.request.user.account_id)

    def get_form_kwargs(self):
        kwargs = super(EditCompanionView, self).get_form_kwargs()

        kwargs.update({
            'user': self.object,
        })

        return kwargs

    def form_valid(self, form):
        form.save()

        return super(EditCompanionView, self).form_valid(form)


class MembersListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """
    View the Members page
    """
    permission_required = 'accounts.can_manage_team'
    template_name = 'account_profile/member_list.html'
    model = User

    def get_queryset(self):
        user_queryset = User.objects.filter(account__id=self.request.user.account_id, is_active=True)
        for user in user_queryset:
            user.can_fly = True if user.has_perm('accounts.can_fly') else False
            user.can_create_itineraries = True if user.has_perm('accounts.can_buy_passes') and user.has_perm('accounts.can_buy_companion_passes') else False
            user.can_book_promo_flights = True if user.has_perm('accounts.can_book_promo_flights') else False
            user.can_manage_companions = True if user.has_perm('accounts.can_manage_companions') else False

        return user_queryset


class MemberReservationsListView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """
    A view to list all of a team member's reservations
    """
    permission_required = 'accounts.can_manage_team'
    template_name = 'account_profile/reservation_list_member.html'
    model = UserProfile
    context_object_name = 'member'

    def get_context_data(self, **kwargs):
        context = super(MemberReservationsListView, self).get_context_data(**kwargs)
        now = arrow.now().datetime

        upcoming_passengers = Passenger.objects.filter(userprofile__id=self.kwargs.get('pk'), flight_reservation__status__in=(FlightReservation.STATUS_RESERVED, FlightReservation.STATUS_CHECKED_IN)).select_related().order_by('flight_reservation__flight__departure')
        flight_reservations = [passenger.flight_reservation for passenger in upcoming_passengers]
        userprofile = self.kwargs.get('pk')

        statuses = (FlightReservation.STATUS_ANYWHERE_PENDING)
        departdate_kwargs = {
            '{0}__{1}'.format('depart_date', 'gte'): now,
        }
        date_kwargs = {
            '{0}__{1}'.format('flight__departure', 'gte'): now,
        }
        id_list = Passenger.objects.filter(userprofile=userprofile, flight_reservation__status__in=statuses).values_list('flight_reservation', flat=True)
        anywhere_reservations = FlightReservation.objects.filter(status__in=statuses, id__in=id_list, **date_kwargs).order_by('flight__departure').select_related()
        profile = UserProfile.objects.filter(id=userprofile).first()
        if profile.user:
            anywhere_requests = AnywhereFlightRequest.objects.filter(created_by_id=profile.user.id, status=AnywhereFlightRequest.STATUS_PENDING,**departdate_kwargs).all()
        else:
            anywhere_requests = []
        waitlist = FlightWaitlist.objects.filter(status=FlightWaitlist.STATUS_WAITING,userprofile=userprofile, **date_kwargs)

        context.update({
            'flight_reservations': flight_reservations,
            'pending_reservations': anywhere_reservations,
            'unapproved_requests': anywhere_requests,
            'waitlist': waitlist
        })

        return context


class DeleteMemberView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    """
    Allows the User to delete a member
    """
    permission_required = 'accounts.can_manage_team'
    template_name = 'account_profile/member_confirm_delete.html'
    model = User
    context_object_name = 'member'
    success_url = reverse_lazy('profile_members')

    def get_queryset(self):
        """
        Ensure the user is on this account
        """
        return User.objects.filter(account__id=self.request.user.account_id)


class AddMemberView(LoginRequiredMixin, PermissionRequiredMixin, FormView):
    """
    Add Member
    """
    permission_required = 'accounts.can_manage_team'
    template_name = 'account_profile/member_add.html'
    form_class = AddEditMemberForm
    success_url = reverse_lazy('profile_members')

    def get_form_kwargs(self):
        kwargs = super(AddMemberView, self).get_form_kwargs()

        kwargs.update({
            'user': self.request.user
        })

        return kwargs

    def get_context_data(self, **kwargs):
        context = super(AddMemberView, self).get_context_data(**kwargs)
        context['fee'] = settings.DEPOSIT_COST
        return context

    def form_valid(self, form):
        user = self.request.user
        acct_full = user.account.is_full()

        first_name = form.cleaned_data.get('first_name')
        last_name = form.cleaned_data.get('last_name')
        email = form.cleaned_data.get('email')

        user_profile = UserProfile(first_name=first_name, last_name=last_name, email = email, account=user.account)
        user_profile.phone = form.cleaned_data.get('phone')
        user_profile.mobile_phone = form.cleaned_data.get('mobile_phone')
        user_profile.date_of_birth = form.cleaned_data.get('date_of_birth')
        user_profile.weight = form.cleaned_data.get('weight')
        user_profile.save()

        member = User.objects.create_user(email, first_name, last_name, None, account=user.account, userprofile=user_profile)

        member_groups = form.cleaned_data.get('member_groups')
        member.groups.add(*member_groups)
        member.save()

        address = Address()

        address.street_1 = form.cleaned_data.get('ship_street_1')
        address.street_2 = form.cleaned_data.get('ship_street_2')
        address.city = form.cleaned_data.get('ship_city')
        address.state = form.cleaned_data.get('ship_state')
        address.postal_code = form.cleaned_data.get('ship_postal_code')
        address.save()

        user_profile.shipping_address = address
        user_profile.save()

        if acct_full and member.has_perm('accounts.can_fly'):
            user.account.member_count= user.account.member_count + 1
            user.account.save()

            # need to charge onboarding fee.
            pm_id = form.cleaned_data.get('payment_method')
            pm = BillingPaymentMethod.objects.filter(id=pm_id).first()
            charge_description = "Add new flying member"
            charge_amt = user.account.get_one_onboarding_fee_total()
            try:
                if pm.payment_method == BillingPaymentMethod.PAYMENT_CREDIT_CARD:
                    card = Card.objects.filter(billing_payment_method_id=pm_id).first()
                    charge = card.charge(charge_amt, charge_description, user)
                else:
                    bankacct = BankAccount.objects.filter(billing_payment_method_id=pm_id).first()
                    charge = bankacct.charge(charge_amt, charge_description, user)

                if charge:
                    charge.send_receipt_email(settings.DEPOSIT_COST, settings.DEPOSIT_COST * settings.DEPOSIT_TAX, settings.DEPOSIT_TAX_PERCENT)

            except Exception as e:
                # we will let RISE know the payment failed but not undo the creation.
                user.account.send_add_member_payment_failed_email(member, user, True)
                member.send_welcome_email()
                messages.info(self.request, 'The new member was added but there was a problem with payment.  Please contact your RISE Representative to assist.')
                return redirect(self.get_success_url())


        member.send_welcome_email()

        messages.info(self.request, 'Successfully added new member')

        return redirect(self.get_success_url())


class EditMemberView(LoginRequiredMixin, PermissionRequiredMixin, FormView):
    """
    Edit Member
    """
    permission_required = 'accounts.can_manage_team'
    template_name = 'account_profile/member_edit.html'
    form_class = AddEditMemberForm
    success_url = reverse_lazy('profile_members')

    @cached_property
    def member(self):
        user = self.request.user
        member_pk = self.kwargs.get('pk')
        member = next(iter(User.objects.filter(id=member_pk, account=user.account)), None)

        if member is None:
            raise Http404

        return member

    def get_initial(self, **kwargs):
        initial = super(EditMemberView, self).get_initial()

        member = self.member

        initial.update({
            'first_name': member.first_name,
            'last_name': member.last_name,
            'email': member.email,
            'phone': member.user_profile.phone,
            'mobile_phone': member.user_profile.mobile_phone,
            'member_groups': member.groups.all(),
            'date_of_birth': member.user_profile.date_of_birth,
            'weight': member.user_profile.weight,
        })

        address = member.user_profile.shipping_address

        if address is not None:
            initial.update({
                'ship_street_1': address.street_1,
                'ship_street_2': address.street_2,
                'ship_city': address.city,
                'ship_state': address.state,
                'ship_postal_code': address.postal_code,
            })

        return initial

    def get_context_data(self, **kwargs):
        context = super(EditMemberView, self).get_context_data(**kwargs)

        if not self.member.has_perm('accounts.can_fly') and self.member.is_coordinator():
            member_paid = False
        else:
            member_paid = True

        context.update({
            'member': self.member,
            'fee': settings.DEPOSIT_COST,
            'member_paid': member_paid,
            'account_is_full':  self.member.account.is_full()
        })

        return context

    def get_form_kwargs(self):
        kwargs = super(EditMemberView, self).get_form_kwargs()

        kwargs.update({
            'user': self.member,
        })

        return kwargs

    def form_valid(self, form):
        member = self.member
        # RISE-500 before updating member, see if they were just a coordinator before (i.e. no onboarding paid)
        if not self.member.has_perm('accounts.can_fly') and self.member.is_coordinator():
            member_paid = False
        else:
            member_paid = True

        member.first_name = form.cleaned_data.get('first_name')
        member.userprofile.first_name = member.first_name

        member.last_name = form.cleaned_data.get('last_name')
        member.userprofile.last_name = member.last_name

        member.email = form.cleaned_data.get('email')
        member.userprofile.email = member.email

        member_groups = form.cleaned_data.get('member_groups')
        groups = member.groups.all()
        for group in groups:
            member.groups.remove(group)

        member.groups.add(*member_groups)
        member.save()
        member.refresh_from_db()

        # RISE-500 see if we need to upgrade the member and charge onboarding.
        # for some reason checking for accounts.can_fly does not work here.  Even with refreshing from db.
        # This logic will have to change if any other groups that are non-flying are added.
        upgrade_member=False
        if not member_paid:
            for group in member.groups.all():
                if group.name != 'Coordinator':
                    upgrade_member=True
                    break

        member.userprofile.phone = form.cleaned_data.get('phone')
        member.userprofile.mobile_phone = form.cleaned_data.get('mobile_phone')
        member.userprofile.date_of_birth = form.cleaned_data.get('date_of_birth')
        member.userprofile.weight = form.cleaned_data.get('weight')

        address = member.user_profile.shipping_address
        if address is None:
            address = Address()

        address.street_1 = form.cleaned_data.get('ship_street_1')
        address.street_2 = form.cleaned_data.get('ship_street_2')
        address.city = form.cleaned_data.get('ship_city')
        address.state = form.cleaned_data.get('ship_state')
        address.postal_code = form.cleaned_data.get('ship_postal_code')
        address.save()

        member.userprofile.shipping_address = address
        member.userprofile.save()
        member.save()

        if member.account.is_full() and upgrade_member:
            member.account.member_count= member.account.member_count + 1
            member.account.save()

            # need to charge onboarding fee.
            pm_id = form.cleaned_data.get('payment_method')
            pm = BillingPaymentMethod.objects.filter(id=pm_id).first()
            charge_description = "Upgrade member to flying member"
            charge_amt = member.account.get_one_onboarding_fee_total()
            try:
                if pm.payment_method == BillingPaymentMethod.PAYMENT_CREDIT_CARD:
                    card = Card.objects.filter(billing_payment_method_id=pm_id).first()
                    charge = card.charge(charge_amt, charge_description, self.request.user)
                else:
                    bankacct = BankAccount.objects.filter(billing_payment_method_id=pm_id).first()
                    charge =bankacct.charge(charge_amt, charge_description, self.request.user)

                if charge:
                    charge.send_receipt_email(settings.DEPOSIT_COST, settings.DEPOSIT_COST * settings.DEPOSIT_TAX, settings.DEPOSIT_TAX_PERCENT)

                messages.info(self.request, 'Member information updated successfully.')

            except Exception as e:
                # we will let RISE know the payment failed but not undo the creation.
                member.account.send_add_member_payment_failed_email(member, self.request.user, True)
                member.send_welcome_email()
                messages.info(self.request, 'The member information was updated but there was a problem with the payment for their membership upgrade.  Please contact your RISE Representative to assist.')
                return redirect(self.get_success_url())

        return super(EditMemberView, self).form_valid(form)


class PersonalInfoView(LoginRequiredMixin, DetailView):
    """
    View the Personal Info page
    """

    template_name = 'account_profile/personal_info.html'
    context_object_name = 'account'

    def get_object(self, queryset=None):
        if self.request.user.is_authenticated():
            user_obj = self.request.user
            account = user_obj.account
            if not account:
                raise Http404
        else:
            raise Http404

        return account


class UpdateOriginAirportView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        origin_pk = request.POST.get('origin_pk', None)
        if origin_pk:
            origin_obj = get_object_or_404(Airport, pk=origin_pk)
            user_obj = request.user
            user_obj.user_profile.origin_airport = origin_obj
            user_obj.user_profile.save()
            json_response = {'success': 'True'}
        else:
            json_response = {'error': 'Origin Airport not found'}

        return HttpResponse(json.dumps(json_response),
            content_type='application/json')


class UpdateUserPermissions(LoginRequiredMixin, PermissionRequiredMixin, View):
    """
    Updates user permissions via AJAX based on the given permission
    """
    permission_required = 'accounts.can_manage_team'

    def post(self, request, *args, **kwargs):
        user_pk = self.kwargs.get('pk')
        user_obj = get_object_or_404(User, pk=user_pk)

        # can_fly = request.POST.get('can_fly', None)
        can_create_itineraries = request.POST.get('can_create_itineraries', None)
        can_book_promo_flights = request.POST.get('can_book_promo_flights', None)
        can_manage_companions = request.POST.get('can_manage_companions', None)

        content_type_user = ContentType.objects.get_for_model(User)

        account_member_group = Group.objects.get(name='Account Member')
        can_buy_passes_permission = Permission.objects.get(content_type=content_type_user, codename='can_buy_passes')
        can_buy_companion_passes_permission = Permission.objects.get(content_type=content_type_user, codename='can_buy_companion_passes')
        can_book_promo_flights_permission = Permission.objects.get(content_type=content_type_user, codename='can_book_promo_flights')
        can_manage_companions_permission = Permission.objects.get(content_type=content_type_user, codename='can_manage_companions')

        # if account_member_group and can_fly:
        #     user_obj.groups.add(account_member_group)
        # elif account_member_group:
        #     user_obj.groups.remove(account_member_group)

        if can_create_itineraries:
            user_obj.user_permissions.add(can_buy_passes_permission)
            user_obj.user_permissions.add(can_buy_companion_passes_permission)
        else:
            user_obj.user_permissions.remove(can_buy_passes_permission)
            user_obj.user_permissions.remove(can_buy_companion_passes_permission)

        if can_book_promo_flights:
            user_obj.user_permissions.add(can_book_promo_flights_permission)
        else:
            user_obj.user_permissions.remove(can_book_promo_flights_permission)

        if can_manage_companions:
            user_obj.user_permissions.add(can_manage_companions_permission)
        else:
            user_obj.user_permissions.remove(can_manage_companions_permission)

        user_obj.save()
        json_response = {'success': 'True'}

        return HttpResponse(json.dumps(json_response),
            content_type='application/json')


class CancelWaitlistView(LoginRequiredMixin, View):

    def get(self, request, *args, **kwargs):
        FlightWaitlist.objects.filter(pk=self.kwargs.get('pk'), user=request.user).update(status=FlightWaitlist.STATUS_CANCELLED)

        messages.info(request, 'You have been removed from the waitlist.')

        return redirect('dashboard')


class ContractView(LoginRequiredMixin, TemplateView):
    template_name = "account_profile/contract_view.html"

    def get_context_data(self, **kwargs):
        context = super(ContractView, self).get_context_data(**kwargs)

        user = self.request.user

        onboarding_fee = settings.DEPOSIT_COST
        context.update({
            'user': user,
            'address': user.user_profile.billing_address,
            'contract': user.account.contract,
            'onboarding_fee': onboarding_fee
        })
        return context
