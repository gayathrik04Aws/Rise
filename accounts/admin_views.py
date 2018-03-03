from django.views.generic import ListView, DetailView, CreateView, UpdateView, FormView, View, DeleteView
from django.views.generic.detail import SingleObjectMixin
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, HttpResponse, Http404, JsonResponse
from django.conf import settings
from django.contrib.auth.models import Group
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from htmlmailer.mailer import send_html_email
from django.utils import timezone
from django.contrib import messages
from django.db.models import Q, Sum, F
from django.utils.functional import cached_property
from django.shortcuts import get_object_or_404, redirect
from django.template.loader import render_to_string
from django.core.mail import send_mail

import json
from dateutil.relativedelta import relativedelta
import datetime
from datetime import timedelta
from billing import paymentMethodUtil
from operator import methodcaller
from auditlog.models import LogEntry
import braintree
import stripe
import arrow
import unicodecsv

from .mixins import StaffRequiredMixin, PermissionRequiredMixin
from .models import Account, User, UserProfile, UserNote, Invite, Address,OncallSchedule, BillingPaymentMethod
from .admin_forms import AccountForm, UserForm, CreditCardForm, ManualChargeForm, RefundChargeForm, UserNoteForm,OnCallScheduleForm, \
    UserProfileForm, StaffUserProfileForm
from .admin_forms import InvitationForm, StaffUserForm, UserPasswordForm, UserFilterForm, BankAccountForm
from .admin_forms import BankAccountVerifyForm, VoidChargeForm
from billing.models import BankAccount, Card, Charge, Subscription, Plan, PlanContractPrice
from reservations.models import Reservation, FlightReservation
from flights.models import Flight

stripe.api_key = settings.STRIPE_API_KEY


class AccountListView(StaffRequiredMixin, PermissionRequiredMixin, ListView):
    """
    A list of all accounts
    """
    permission_required = 'accounts.can_view_members'
    model = Account
    template_name = 'admin/accounts/account_list.html'
    queryset = Account.objects.all().select_related('plan')

    def get_context_data(self, **kwargs):
        context = super(AccountListView, self).get_context_data(**kwargs)

        search_param = self.request.GET.get('s', None)
        search_on = None
        if search_param:
            search_on = search_param

        if search_on:
            # TODO: Expand search to an indexing implementation like Elastic Search
            self.queryset = self.queryset.filter(
                Q(company_name__icontains=search_on) |
                Q(primary_user__first_name__icontains=search_on) |
                Q(primary_user__last_name__icontains=search_on) |
                Q(primary_user__email__icontains=search_on) |
                Q(plan__name__icontains=search_on) |
                Q(plan__description__icontains=search_on)
            )

        context.update({
            'sorted_accounts': sorted(self.queryset, key=methodcaller('account_name'))
        })

        return context


class AccountDetailView(StaffRequiredMixin, PermissionRequiredMixin, DetailView):
    """
    A detail view of an account
    """

    permission_required = 'accounts.can_view_members'
    model = Account
    template_name = 'admin/accounts/account_detail.html'

    def dispatch(self, request, *args, **kwargs):
        if self.request.session.get('pay_path', None) is not None:
            del request.session['pay_path']
        return super(AccountDetailView, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(AccountDetailView, self).get_context_data(**kwargs)

        recent_charges = self.object.charge_set.all().order_by('-id')[:5]

        start = arrow.now().floor('day')

        upcoming_flight_reservations = FlightReservation.objects.filter(
            reservation__account=self.object,  # reservations for this account
            reservation__status=Reservation.STATUS_RESERVED,  # that have been reserved
            status__in=(FlightReservation.STATUS_RESERVED, FlightReservation.STATUS_CHECKED_IN),  # that are reserved or checked in
            flight__departure__gte=start.datetime
        ).order_by('flight__departure')[:5]  # ordered by departure time and limited to 5

        context.update({
            'recent_charges': recent_charges,
            'upcoming_flight_reservations': upcoming_flight_reservations,
            'corporate_accounts': Account.objects.filter(account_type=Account.TYPE_CORPORATE).order_by('company_name'),
            'fee': settings.DEPOSIT_COST
        })

        return context


class AccountMergeView(StaffRequiredMixin, PermissionRequiredMixin, SingleObjectMixin, View):
    """
    A view to merge an individual account into a corporate account
    """

    permission_required = 'accounts.can_merge_accounts'
    model = Account

    def post(self, request, *args, **kwargs):
        # get the current account/user
        current_account = self.get_object()
        user = current_account.primary_user
        userprofile = current_account.primary_profile

        # get the corpoprate account to merge into
        corporate_account_id = request.POST.get('account_id')
        corporate_account = Account.objects.get(id=corporate_account_id)
        user.account = corporate_account
        userprofile.account = corporate_account

        userprofile.save()

        # if the account is full, add as a Coordinator else an account member who can fly
        if corporate_account.is_full():
            group = Group.objects.get(name='Coordinator')
        else:
            group = Group.objects.get(name='Account Member')

        # clear and reset groups
        user.groups.clear()
        user.groups.add(group)

        user.save()

        # get reservation totals for passes used by the old account
        reservation_totals = FlightReservation.objects.filter(
            status__in=(FlightReservation.STATUS_PENDING, FlightReservation.STATUS_RESERVED, FlightReservation.STATUS_CHECKED_IN),
            reservation__account=current_account
        ).aggregate(
            pass_count=Sum('pass_count'),
            complimentary_pass_count=Sum('complimentary_pass_count'),
            companion_pass_count=Sum('companion_pass_count'),
            complimentary_companion_pass_count=Sum('complimentary_companion_pass_count'),
        )

        # get counts or 0s
        pass_count = reservation_totals.get('pass_count', 0) or 0
        complimentary_pass_count = reservation_totals.get('complimentary_pass_count', 0) or 0
        companion_pass_count = reservation_totals.get('companion_pass_count', 0) or 0
        complimentary_companion_pass_count = reservation_totals.get('complimentary_companion_pass_count', 0) or 0

        # update the new corporate account with these pass counts
        Account.objects.filter(id=corporate_account.id).update(
            available_passes=F('available_passes') - pass_count,
            available_companion_passes=F('available_companion_passes') - companion_pass_count,
            complimentary_passes=F('complimentary_passes') - complimentary_pass_count,
            complimentary_companion_passes=F('complimentary_companion_passes') - complimentary_companion_pass_count,
        )

        # refresh model and cache
        corporate_account.refresh_from_db()
        corporate_account.refresh_cache()

        # update reservations from the old account to point to the new new corporate account
        Reservation.objects.filter(account=current_account).update(account=corporate_account)

        # cancel the old account
        current_account.status = Account.STATUS_CANCELLED
        current_account.primary_user = None
        current_account.primary_profile = None
        current_account.save()

        # cancel the old subscription
        subscription = current_account.get_subscription()
        if subscription is not None:
            subscription.cancel(refund=True, user=request.user)

        return JsonResponse({})


class AccountAuditView(StaffRequiredMixin, PermissionRequiredMixin, DetailView):
    """
    An audit view of an account
    """

    permission_required = 'accounts.can_view_members'
    model = Account
    template_name = 'admin/accounts/account_audit.html'

    def get_context_data(self, **kwargs):
        context = super(AccountAuditView, self).get_context_data(**kwargs)

        logs = LogEntry.objects.get_for_object(self.object)

        context.update({
            'logs': logs,
        })

        return context


class AccountCreateView(StaffRequiredMixin, PermissionRequiredMixin, CreateView):
    """
    A create view to allow admin to create an account
    """

    permission_required = 'accounts.can_edit_members'
    model = Account
    template_name = 'admin/accounts/account_form.html'
    form_class = AccountForm

    def get_initial(self):
        """
        Returns the initial data to use for forms on this view.
        """
        initial = super(AccountCreateView, self).get_initial()
        plan = Plan.objects.filter(name='Express').first()
        initial['plan'] = plan
        initial['contract'] = PlanContractPrice.objects.filter(plan_id=plan.id, contract_length=12).first()

        return initial

    def get_form_kwargs(self):
        kwargs = super(AccountCreateView, self).get_form_kwargs()

        kwargs.update({
            'user': self.request.user
        })
        return kwargs

    def form_valid(self, form):
        self.object = account = form.save(commit=False)

        if not account.is_corporate():
            if account.plan is not None:
                account.pass_count = account.plan.pass_count
                account.companion_pass_count = account.plan.companion_passes
            else:
                account.pass_count = 0
                account.companion_pass_count = 0
        else:
            account.contract=None
            account.plan=Plan.objects.filter(name='Executive').first()

        account.available_passes = account.pass_count
        account.available_companion_passes = account.companion_pass_count

        account.save()

        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse('admin_account_add_user', args=(self.object.pk,))


class ContractChoicesView(View):
    def get(self, request, *args, **kwargs):
        choicelist = []
        selected_plan_id = request.GET.get('plan')
        contracts = PlanContractPrice.objects.filter(plan_id=selected_plan_id).all()
        for contract in contracts:
            val = [contract.id, contract.__str__()]
            choicelist.append(val)
        jsonresult = json.dumps(choicelist)
        return HttpResponse(jsonresult, content_type='application/javascript')

class ContractChoicesViewSeparateFields(View):
    def get(self, request, *args, **kwargs):
        choicelist = []
        selected_plan_id = request.GET.get('plan')
        contracts = PlanContractPrice.objects.filter(plan_id=selected_plan_id).all()
        for contract in contracts:
            val = [contract.id, contract.contract_length, str(contract.amount)]
            choicelist.append(val)
        jsonresult = json.dumps(choicelist)
        return HttpResponse(jsonresult, content_type='application/javascript')

class AccountUpdateView(StaffRequiredMixin, PermissionRequiredMixin, UpdateView):
    """
    A view to edit an account
    """

    permission_required = 'accounts.can_edit_members'
    model = Account
    template_name = 'admin/accounts/account_form.html'
    context_object_name = 'account'
    form_class = AccountForm

    def get_form_kwargs(self):
        kwargs = super(AccountUpdateView, self).get_form_kwargs()

        kwargs.update({
            'user': self.request.user,
        })

        return kwargs


    def get_success_url(self):
        """
        Go back to account detail view
        """
        return reverse('admin_account', args=(self.object.pk,))

    def form_valid(self, form):
        old_status = self.get_object().get_status_display()
        # permission checks that involve charges to an account
        old_plan = self.get_object().plan
        if 'plan' in form.changed_data:
            new_plan = form.cleaned_data.get('plan')
            if (not self.request.user.has_perm('accounts.can_charge_members') and new_plan.amount > old_plan.amount):
                messages.error(self.request, 'Sorry. You need to be an Admin to change an account plan that incurs a surcharge.')
                return HttpResponseRedirect(self.get_success_url())
            else:
                messages.info(self.request, 'Plan was changed.')

            if new_plan.requires_contract and not 'contract' in form.cleaned_data:
                messages.error(self.request, 'The selected plan requires a contract be selected.')
                return HttpResponseRedirect(self.get_success_url())

        if 'contract' in form.changed_data:
            new_contract = form.cleaned_data.get('contract')
            old_plan = self.get_object().plan
            self.object.contract = new_contract


            if new_contract:
                if not new_contract.plan == old_plan:
                    new_plan = new_contract.plan

                    if (not self.request.user.has_perm('accounts.can_charge_members') and new_plan.amount > old_plan.amount):
                        messages.error(self.request, 'Sorry. You need to be an Admin to change an account plan that incurs a surcharge.')
                        return HttpResponseRedirect(self.get_success_url())
                    else:
                        messages.info(self.request, 'Contract was changed.')
            else:
                messages.info(self.request, 'Contract was removed since the user has downgraded to a non-contract membership.')


        if 'corporate_amount' in form.changed_data:
            corporate_amount = form.cleaned_data.get('corporate_amount')
            old_corporate_amount = self.get_object().corporate_amount
            if (not self.request.user.has_perm('accounts.can_charge_members') and corporate_amount > old_corporate_amount):
                messages.error(self.request, 'Sorry. You need to be an Admin to increase the corporate payment amount for an account.')
                return HttpResponseRedirect(self.get_success_url())

        self.object = account = form.save()
        if account.primary_profile is not None:
            account.primary_user = User.objects.filter(userprofile=account.primary_profile).first()
            account.save()

        if 'contract' in form.changed_data:
            if new_contract == None:
                # clear out contract dates
                account.contract_start_date = None
                account.contract_end_date = None
                account.save()

            elif account.status == Account.STATUS_ACTIVE:
                # need to update the contract dates if they pick new contract for existing active acct.
                # If they are just being activated now, this will happen below during subscription creation
                account.contract_start_date = datetime.datetime.now()
                account.contract_end_date = account.contract_start_date + relativedelta(months=account.contract.contract_length)
                account.save()

        # if the account type changes between corporate or Individual
        if 'account_type' in form.changed_data:
            account_type = form.cleaned_data.get('account_type')
            # if changing the account to a corporate account
            if account_type == Account.TYPE_CORPORATE:
                # update the primary user to be the Corporate Account Admin
                if account.primary_user is not None:
                    account.primary_user.groups.clear()
                    account.primary_user.groups.add(Group.objects.get(name='Corporate Account Admin'))

            else:  # changing to an Individual account
                # update the primary user to be the Individual Account Admin
                if account.primary_user is not None:
                    account.primary_user.groups.clear()
                    account.primary_user.groups.add(Group.objects.get(name='Individual Account Admin'))

        new_subscription = None
        if 'status' in form.changed_data:
            status = form.cleaned_data.get('status')
            subscription = account.get_subscription()
            if status == Account.STATUS_ACTIVE:
                if subscription is None and not account.is_corporate():
                    override=False
                    # special rule for founders w/in 1 yr of activation.
                    if account.founder and account.activated:
                        now = datetime.datetime.now()
                        delta = now.date() - account.activated.date()
                        if delta.days < 365:
                            lastsubscription = account.subscription_set.order_by('-period_end', '-created').first()
                            if lastsubscription:
                                new_subscription = Subscription.objects.create_subscription(account, created_by=self.request.user, override_amount=lastsubscription.amount)
                                override = True
                    if not override:
                        new_subscription = Subscription.objects.create_subscription(account, created_by=self.request.user)
                if account.contract and not account.contract_end_date:
                    account.contract_start_date = datetime.datetime.now()
                    account.contract_end_date = account.contract_start_date + relativedelta(months=account.contract.contract_length)
                    account.save()
                # if the account has not been through the typical on-boarding process for some reason
                if account.activated is None:
                    if account.is_corporate():
                        admin_group = Group.objects.get(name='Corporate Account Admin')

                        account.available_passes = account.pass_count
                        account.available_companion_passes = account.companion_pass_count
                    else:
                        admin_group = Group.objects.get(name='Individual Account Admin')
                        account.pass_count = account.plan.pass_count
                        account.companion_pass_count = account.plan.companion_passes

                        account.available_passes = account.plan.pass_count
                        account.available_companion_passes = account.plan.companion_passes

                    if not account.primary_user.groups.filter(id=admin_group.id).exists():
                        account.primary_user.groups.add(admin_group)

                    account.activated = arrow.now().datetime
                    account.save()
            else:
                if subscription is not None:
                    subscription.cancel(refund=False, user=self.request.user)

            # notify rise management about status changes
            subject = "Status update to %s" % (account.account_name())
            from_email = 'Rise <info@iflyrise.com>'
            to_emails = ['nick@iflyrise.com', 'megan@iflyrise.com', ]

            context = {
                'subject': subject,
                'name': self.request.user.get_full_name(),
                'account_name': account.account_name,
                'old_status': old_status,
                'new_status': account.get_status_display()
            }

            text_content = render_to_string('emails/admin_account_status_change.txt', context)

            send_mail(subject, text_content, from_email, to_emails)

        if account.is_corporate():

            if not account.onboarding_fee_paid and account.is_active():
                onboarding_fee = account.get_onboarding_fee_total()
                description = 'Fee for %d team members ($%d/member) + %s tax' % (account.member_count, settings.DEPOSIT_COST, settings.DEPOSIT_TAX_PERCENT)
                charge = account.charge(onboarding_fee, description, self.request.user)
                charge.send_receipt_email()
                account.onboarding_fee_paid = True
                account.save()

            if 'corporate_amount' in form.changed_data or 'account_type' in form.changed_data or 'status' in form.changed_data:
                if account.is_active():
                    account.plan = Plan.objects.filter(name='Executive').first()
                    account.contract=None
                    account.save()
                    subscription = account.get_subscription()
                    if subscription is not None:
                        if subscription.amount == 0:
                            subscription.cancel(refund=False, user=self.request.user)
                            Subscription.objects.create_subscription(account, created_by=self.request.user)
                        else:
                            description = '%s Subscription' % (account.account_name(),)
                            subscription.description=description
                            subscription.save()
                            subscription.update_amount(account.corporate_amount,user=self.request.user)
                    else:
                        override=False
                        # special rule for founders w/in 1 yr of activation.
                        if account.founder and account.activated:
                            now = datetime.datetime.now()
                            delta = now.date() - account.activated.date()
                            if delta.days < 365:
                                lastsubscription = account.subscription_set.order_by('-period_end', '-created').first()
                                if lastsubscription:
                                    new_subscription = Subscription.objects.create_subscription(account, created_by=self.request.user, override_amount=lastsubscription.amount)
                                    override = True
                        if not override:
                            Subscription.objects.create_subscription(account, created_by=self.request.user)

            if 'pass_count' in form.changed_data:
                passes_in_use = account.passes_in_use()
                pass_total = account.pass_count
                account.available_passes = pass_total - passes_in_use
                account.save()

            if 'companion_pass_count' in form.changed_data:
                companion_passes_in_use = account.companion_passes_in_use()
                companion_pass_total = account.companion_pass_count
                account.available_companion_passes = companion_pass_total - companion_passes_in_use
                account.save()
        else:
            if 'plan' in form.changed_data or 'contract' in form.changed_data:
                # runs after form.save() in order to have the pass counts up to date
                account.change_plan(account.plan, force=True, contract=account.contract,user=self.request.user)

        account.refresh_cache()

        return HttpResponseRedirect(self.get_success_url())


class UserListView(StaffRequiredMixin, PermissionRequiredMixin, ListView):
    """
    A list of all users
    """

    permission_required = 'accounts.can_view_members'
    # need to refactor this to be a userprofile view
    model = UserProfile
    template_name = 'admin/accounts/user_list.html'

    def get_context_data(self, **kwargs):
        context = super(UserListView, self).get_context_data(**kwargs)

        context.update({
            'user_filter_form': UserFilterForm(initial={'filter_on': ''}),
        })

        return context

    def get_queryset(self):
        # need to query userprofile not user
        queryset = UserProfile.objects.exclude(account=None).order_by('first_name')

        search_param = self.request.GET.get('s', None)
        search_on = None
        if search_param:
            search_on = search_param

        if search_on:
            # TODO: Expand search to an indexing implementation like Elastic Search
            queryset = queryset.filter(
                Q(first_name__icontains=search_on) |
                Q(last_name__icontains=search_on) |
                Q(email__icontains=search_on) |
                Q(title__icontains=search_on) |
                Q(phone__icontains=search_on) |
                Q(mobile_phone__icontains=search_on) |
                Q(account__company_name__icontains=search_on)
            )

        return queryset


class UserDetailView(StaffRequiredMixin, PermissionRequiredMixin, DetailView):
    """
    A view to show user details
    """

    permission_required = 'accounts.can_view_members'
    model = UserProfile
    template_name = 'admin/accounts/user_detail.html'
    context_object_name = 'account_user'


class UserCreateView(StaffRequiredMixin, PermissionRequiredMixin, FormView):
    """
    A view to add an userprofile + user to an account
    """

    permission_required = 'accounts.can_edit_members'
    model = UserProfile
    template_name = 'admin/accounts/user_form.html'
    form_class = UserProfileForm

    '''
    def get_initial(self):
        initial = super(UserCreateView, self).get_initial()
        initial.update({
            "groups": []
        })
        return initial
    '''

    def get_context_data(self, **kwargs):
        context = super(UserCreateView, self).get_context_data(**kwargs)
        context['fee'] = settings.DEPOSIT_COST
        self.account_pk = self.kwargs.get('pk')
        self.account = get_object_or_404(Account, pk=self.account_pk)
        context['account'] = self.account
        context['is_staff'] = False
        return context

    def get_form_kwargs(self):
        kwargs = super(UserCreateView, self).get_form_kwargs()
        self.account_pk = self.kwargs.get('pk')
        self.account = get_object_or_404(Account, pk=self.account_pk)
        kwargs.update({
            'account': self.account,
            'member': None,
        })
        return kwargs

    def form_valid(self, form):
        account_pk = self.kwargs.get('pk')
        account = Account.objects.filter(id=account_pk).first()
        acct_full = account.is_full()

        #self.object = userprofile = form.save(commit=False)
        userprofile = form.save(account_pk, None)

        user = userprofile.user

        if user.account.primary_user is None:
            user.account.primary_user = user
            user.account.primary_profile = userprofile
            user.account.save()

        if user.account.primary_user == user:
            if user.account.plan and user.account.plan.anywhere_only:
                user.send_anywhere_onboarding_email(flightset=None, flight_creator=None)
            else:
                user.send_onboarding_email()
            messages.info(self.request, 'Onboarding email sent to %s at %s' % (user.get_full_name(), user.email))
        else:
            if user.account.is_corporate():
                messages.info(self.request, 'Welcome email sent to %s at %s' % (user.get_full_name(), user.email))
                user.send_welcome_email()
            else:
                pass
                # TODO: send companion welcome email

        if acct_full and user.has_perm('accounts.can_fly') and not user.is_staff and not user.is_companion:
            user.account.member_count= user.account.member_count + 1
            user.account.save()

            override_charge = form.cleaned_data.get("override_charge")
            if not override_charge or override_charge==False:
                # need to charge onboarding fee.
                pm_id = form.cleaned_data.get('payment_method')
                pm = BillingPaymentMethod.objects.filter(id=pm_id).first()
                charge_description = "Add new flying member"
                charge_amt = user.account.get_one_onboarding_fee_total()
                try:
                    if pm.payment_method == BillingPaymentMethod.PAYMENT_CREDIT_CARD:
                        card = Card.objects.filter(billing_payment_method_id=pm_id).first()
                        charge = card.charge(charge_amt, charge_description, self.request.user)
                    else:
                        bankacct = BankAccount.objects.filter(billing_payment_method_id=pm_id).first()
                        charge = bankacct.charge(charge_amt, charge_description, self.request.user)

                    if charge:
                        charge.send_receipt_email(settings.DEPOSIT_COST, settings.DEPOSIT_COST * settings.DEPOSIT_TAX, settings.DEPOSIT_TAX_PERCENT)

                except Exception as e:
                    # we will let RISE know the payment failed but not undo the creation.
                    user.account.send_add_member_payment_failed_email(user, self.request.user, True)
                    user.send_welcome_email()
                    messages.info(self.request, 'The new member was added but there was a problem with payment: %s' % e.message)

        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        #account = self.object.account
        pk = self.kwargs.get('pk')
        return reverse('admin_account', args=(pk,))


class UserUpdateView(StaffRequiredMixin, PermissionRequiredMixin, FormView):
    """
    A view to update a user
    """

    permission_required = 'accounts.can_edit_members'
    model = UserProfile
    template_name = 'admin/accounts/user_form.html'
    form_class = UserProfileForm
    context_object_name = 'member'

    def get_initial(self, *args, **kwargs):
        initial = super(UserUpdateView, self).get_initial()
        pk = self.kwargs.get('pk')
        user_profile = UserProfile.objects.filter(id=pk).first()
        if user_profile.user:
            groups = user_profile.user.groups.all()


        try:
            initial.update({
                'first_name': user_profile.first_name,
                'last_name': user_profile.last_name,
                'email': user_profile.email,
                'phone': user_profile.phone,
                'mobile_phone': user_profile.mobile_phone,
                'date_of_birth': user_profile.date_of_birth,
                'weight': user_profile.weight,
                'food_options': user_profile.food_options.all(),
                'allergies': user_profile.allergies,
                'origin_airport': user_profile.origin_airport,
                'groups': groups,
                'is_active': user_profile.user.is_active
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

    def get_context_data(self, **kwargs):
        context = super(UserUpdateView, self).get_context_data(**kwargs)

        self.userprofile_pk = self.kwargs.get('pk')
        self.userprofile = UserProfile.objects.get(id=self.userprofile_pk)
        if self.userprofile.user:
            is_staff = self.userprofile.user.is_staff
        else:
            is_staff=False
        if not self.userprofile.user  or self.userprofile.user.is_companion() or (not self.userprofile.user.can_fly() and (self.userprofile.user.is_coordinator())):
            member_paid = False
        else:
            member_paid = True
        context.update({
            'account': self.userprofile.account,
            'member': self.userprofile,
            'is_staff': is_staff,
            'member_paid': member_paid,
            'fee': settings.DEPOSIT_COST
        })

        return context

    def get_form_kwargs(self):
        kwargs = super(UserUpdateView, self).get_form_kwargs()
        self.userprofile_pk = self.kwargs.get('pk')
        self.userprofile = UserProfile.objects.get(id=self.userprofile_pk)
        kwargs.update({
            'account': self.userprofile.account,
            'member': self.userprofile,
        })
        return kwargs

    def form_valid(self, form):
        acct_full = self.userprofile.account.is_full()
        flying_member_before = False
        user = self.userprofile.user
        # if they only have userprofile and not user and aren't a companion, they are not a member.
        if user and user.can_fly() and not user.is_companion():
            flying_member_before=True

        form.save(self.userprofile.account_id, self.userprofile)

        if acct_full and user and not flying_member_before and not user.is_staff:
            # see if they are a flying member now
            upgrade_member=False
            for group in user.groups.all():
                if group.name != 'Coordinator' and group.name != 'Companion':
                    upgrade_member=True
                    break

            if upgrade_member:
                user.account.member_count= user.account.member_count + 1
                user.account.save()

                override_charge = form.cleaned_data.get("override_charge")
                if not override_charge or override_charge==False:
                    # need to charge onboarding fee.
                    pm_id = form.cleaned_data.get('payment_method')
                    if not pm_id:
                        form.add_error("payment_method","You must select a payment method.")
                        return self.form_invalid(form)
                    pm = BillingPaymentMethod.objects.filter(id=pm_id).first()
                    charge_description = "Upgrade member to flying member"
                    charge_amt = user.account.get_one_onboarding_fee_total()
                    try:
                        if pm.payment_method == BillingPaymentMethod.PAYMENT_CREDIT_CARD:
                            card = Card.objects.filter(billing_payment_method_id=pm_id).first()
                            charge = card.charge(charge_amt, charge_description, self.request.user)
                        else:
                            bankacct = BankAccount.objects.filter(billing_payment_method_id=pm_id).first()
                            charge = bankacct.charge(charge_amt, charge_description, self.request.user)

                        # send billing receipt

                        if charge:
                            charge.send_receipt_email(settings.DEPOSIT_COST, settings.DEPOSIT_COST * settings.DEPOSIT_TAX, settings.DEPOSIT_TAX_PERCENT)

                    except Exception as e:
                        # we will let RISE know the payment failed but not undo the creation.
                        user.account.send_add_member_payment_failed_email(user, self.request.user, True)
                        user.send_welcome_email()
                        messages.info(self.request, 'The member was upgraded, but there was a problem with payment: %s' % e.message)


        return super(UserUpdateView, self).form_valid(form)

    def get_success_url(self):
        return reverse('admin_account_user', args=(self.userprofile.account_id ,self.userprofile_pk))


class UserAddNoteView(StaffRequiredMixin, PermissionRequiredMixin, CreateView):
    """
    A view to add a note regarding a user
    """

    permission_required = 'accounts.can_edit_members'
    model = UserNote
    template_name = 'admin/accounts/user_note_form.html'
    form_class = UserNoteForm

    def get_form_kwargs(self):
        kwargs = super(UserAddNoteView, self).get_form_kwargs()
        self.account_pk = self.kwargs.get('account_pk')
        self.account = get_object_or_404(Account, pk=self.account_pk)
        self.member_pk = self.kwargs.get('member_pk')
        self.member = get_object_or_404(UserProfile, pk=self.member_pk)
        kwargs.update({
            'account': self.account,
            'member': self.member,
        })
        return kwargs

    def form_valid(self, form):
        self.object = user_note = form.save(commit=False)

        account_pk = self.kwargs.get('account_pk')
        member_pk = self.kwargs.get('member_pk')

        user_note.created_by_id = self.request.user.id

        user_note.save()

        return HttpResponseRedirect(reverse('admin_account_user', args=(account_pk, member_pk,)))


class UserNoteListView(StaffRequiredMixin, PermissionRequiredMixin, ListView):
    """
    A list of notes for a user
    """

    permission_required = 'accounts.can_view_members'
    model = UserNote
    template_name = 'admin/accounts/user_note_list.html'

    def get_context_data(self, **kwargs):
        context = super(UserNoteListView, self).get_context_data(**kwargs)

        member_pk = self.kwargs.get('member_pk', None)
        member = get_object_or_404(UserProfile, pk=member_pk)

        context.update({
            'member': member,
        })

        return context

    def get_queryset(self):
        member_pk = self.kwargs.get('member_pk', None)
        return UserNote.objects.filter(userprofile_id=member_pk).order_by('-created')


class UserNoteDetailView(StaffRequiredMixin, PermissionRequiredMixin, DetailView):
    """
    A view to show note details
    """

    permission_required = 'accounts.can_view_members'
    model = UserNote
    template_name = 'admin/accounts/user_note_detail.html'
    context_object_name = 'user_note'

    def get_context_data(self, **kwargs):
        context = super(UserNoteDetailView, self).get_context_data(**kwargs)

        member_pk = self.kwargs.get('member_pk', None)
        member = get_object_or_404(UserProfile, pk=member_pk)

        context.update({
            'member': member,
        })

        return context


class StaffListView(StaffRequiredMixin, PermissionRequiredMixin, ListView):
    """
    A list of all staff users (`User.is_staff()` is True`)
    """

    permission_required = 'accounts.can_manage_staff'
    model = User
    template_name = 'admin/accounts/staff_list.html'

    def get_queryset(self):
        return User.objects.filter(is_active=True, is_staff=True).order_by('first_name')


class StaffUserDetailView(StaffRequiredMixin, PermissionRequiredMixin, DetailView):
    """
    A view to show staff user details
    """

    permission_required = 'accounts.can_manage_staff'
    model = User
    template_name = 'admin/accounts/staff_user_detail.html'
    context_object_name = 'account_user'


class StaffUserCreateView(StaffRequiredMixin, PermissionRequiredMixin, FormView):
    """
    A view to add a staff user
    """

    permission_required = 'accounts.can_manage_staff'
    model = UserProfile
    template_name = 'admin/accounts/staff_user_form.html'
    form_class = StaffUserProfileForm

    def form_valid(self, form):
        userprofile = form.save(None)

        userprofile.user.send_staff_welcome_email()

        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse('admin_staff')


class StaffUserUpdateView(StaffRequiredMixin, PermissionRequiredMixin, FormView):
    """
    A view to update a staff user
    """

    permission_required = 'accounts.can_manage_staff'
    model = UserProfile
    template_name = 'admin/accounts/staff_user_form.html'
    form_class = StaffUserProfileForm
    context_object_name = 'member'

    def get_initial(self, *args, **kwargs):
        initial = super(StaffUserUpdateView, self).get_initial()
        pk = self.kwargs.get('pk')
        user_profile = UserProfile.objects.filter(id=pk).first()
        if user_profile.user:
            groups = user_profile.user.groups.all()


        try:
            initial.update({
                'first_name': user_profile.first_name,
                'last_name': user_profile.last_name,
                'email': user_profile.email,
                'phone': user_profile.phone,
                'mobile_phone': user_profile.mobile_phone,
                'date_of_birth': user_profile.date_of_birth,
                'weight': user_profile.weight,
                'food_options': user_profile.food_options.all(),
                'allergies': user_profile.allergies,
                'origin_airport': user_profile.origin_airport,
                'groups': groups,
                'account': user_profile.account
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

    def get_context_data(self, **kwargs):
        context = super(StaffUserUpdateView, self).get_context_data(**kwargs)

        self.userprofile_pk = self.kwargs.get('pk')
        self.userprofile = UserProfile.objects.get(id=self.userprofile_pk)
        context.update({
            'account': self.userprofile.account,
            'member': self.userprofile,
        })

        return context


    def form_valid(self, form):
        userprofile_pk = self.kwargs.get('pk')
        userprofile = UserProfile.objects.get(id=userprofile_pk)

        form.save(userprofile)

        return super(StaffUserUpdateView, self).form_valid(form)

    def get_success_url(self):
        return reverse('admin_staff')


class AccountCreditCardView(StaffRequiredMixin, PermissionRequiredMixin, FormView):
    """
    A view to add or update an account's credit card payment method
    """

    permission_required = 'accounts.can_edit_members'
    form_class = CreditCardForm
    template_name = 'admin/accounts/credit_card_form.html'

    @cached_property
    def account(self):
        return Account.objects.get(pk=self.kwargs.get('pk'))

    def get_context_data(self, **kwargs):
        context = super(AccountCreditCardView, self).get_context_data(**kwargs)
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

        pay_path = self.request.session.get('pay_path', None)

        if pay_path:
            del self.request.session['pay_path']
            return HttpResponseRedirect(pay_path)

        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse('admin_account', args=(self.account.pk,))


class AccountBankAccountView(StaffRequiredMixin, PermissionRequiredMixin, FormView):
    """
    A view to update an account's bank account
    """

    permission_required = 'accounts.can_edit_members'
    form_class = BankAccountForm
    template_name = 'admin/accounts/bank_account_form.html'

    @cached_property
    def account(self):
        return Account.objects.get(pk=self.kwargs.get('pk'))

    def get_context_data(self, **kwargs):
        context = super(AccountBankAccountView, self).get_context_data(**kwargs)

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

        nickname = form.cleaned_data.get('nickname')
        paymentMethodUtil.createBankAccount(self.account.id, token, nickname)
        routing = form.cleaned_data.get('routing')
        last4 = form.cleaned_data.get('last4')
        try:
            paymentMethodUtil.createBankAccount(self.account.id, token, form.cleaned_data.get('nickname'), routing=routing, last4=last4)
        except paymentMethodUtil.CardException as e:
            for error in e.message:
                form.add_error(None,error)
            return self.form_invalid(form)

        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse('admin_account', args=(self.account.pk,))


class AccountBankAccountVerifyView(StaffRequiredMixin, PermissionRequiredMixin, FormView):
    """
    A view to update an account's bank account
    """

    permission_required = 'accounts.can_edit_members'
    form_class = BankAccountVerifyForm
    template_name = 'admin/accounts/bank_account_verify_form.html'

    def form_valid(self, form):
        verify_1 = int(form.cleaned_data.get('verify_1') * 100)
        verify_2 = int(form.cleaned_data.get('verify_2') * 100)

        self.account = Account.objects.get(pk=self.kwargs.get('pk'))
        stripe_customer = self.account.get_stripe_customer()
        bank_account = self.account.get_bank_account()
        if bank_account is not None:
            stripe_bank_account = stripe_customer.bank_accounts.retrieve(bank_account.stripe_id)
        else:
            return self.form_invalid(form)

        if not stripe_bank_account.verified:
            try:
                stripe_bank_account = stripe_bank_account.verify(amounts=(verify_1, verify_2))
                # stripe_bank_account = stripe_customer.bank_accounts.retrieve(stripe_customer.default_bank_account)
                bank_account.update_from_stripe_bank_account(stripe_bank_account)
                bank_account.save()
            except Exception, e:
                form.add_error(None, e.message)
                return self.form_invalid(form)
        else:
            bank_account.verified = True
            bank_account.save()

        pay_path = self.request.session.get('pay_path', None)

        if pay_path:
            self.request.session.delete('pay_path')
            return HttpResponseRedirect(pay_path)

        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse('admin_account', args=(self.account.pk,))


class AccountDeleteBankAccountView(StaffRequiredMixin, PermissionRequiredMixin, View):
    """
    A view to delete a bank account from an account
    """

    permission_required = 'accounts.can_edit_members'

    def get(self, request, *args, **kwargs):
        bank_id = self.kwargs.get('card')
        account_id=self.kwargs.get('pk')
        paymentMethodUtil.deleteBankAccountView(bank_id, account_id)
        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse('admin_account', args=(self.kwargs.get('pk'),))


class DefaultPayMethodView(StaffRequiredMixin, PermissionRequiredMixin, View):

    permission_required = 'accounts.can_edit_members'

    def get(self, request, *args, **kwargs):
        billing_payment_method_id = self.kwargs.get('method')
        account_id=self.kwargs.get('pk')
        paymentMethodUtil.setDefaultPayment(billing_payment_method_id, account_id)
        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse('admin_account', args=(self.kwargs.get('pk'),))


class AccountDeleteCreditCardView(StaffRequiredMixin, PermissionRequiredMixin, View):
    """
    A view to delete a bank account from an account
    """

    permission_required = 'accounts.can_edit_members'

    def get(self, request, *args, **kwargs):
        card_id = self.kwargs.get('card')
        account_id=self.kwargs.get('pk')
        paymentMethodUtil.deleteCreditCard(card_id)
        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse('admin_account', args=(self.kwargs.get('pk'),))


class AccountChargeListView(StaffRequiredMixin, PermissionRequiredMixin, ListView):
    """
    A list of all charges for an account
    """

    permission_required = 'accounts.can_view_members'
    model = Charge
    template_name = 'admin/accounts/charge_list.html'

    def get_queryset(self):
        return Charge.objects.filter(account__id=self.kwargs.get('pk')).order_by('-id')

    def dispatch(self, request, *args, **kwargs):
        if self.request.session.get('pay_path', None) is not None:
            del request.session['pay_path']
        return super(AccountChargeListView, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(AccountChargeListView, self).get_context_data(**kwargs)

        context.update({
            'account': Account.objects.get(pk=self.kwargs.get('pk'))
        })

        return context


class AccountChargeCreateView(StaffRequiredMixin, PermissionRequiredMixin, CreateView):
    """
    A view to add a charge for manual payments
    """

    permission_required = 'accounts.can_charge_members'
    model = Charge
    template_name = 'admin/accounts/charge_form.html'
    form_class = ManualChargeForm

    @cached_property
    def account(self):
        return Account.objects.get(pk=self.kwargs.get('pk'))

    def get_form_kwargs(self):
        kwargs = super(AccountChargeCreateView, self).get_form_kwargs()

        kwargs.update({
            'account': self.account,
        })

        return kwargs

    def get_context_data(self, **kwargs):
        context = super(AccountChargeCreateView, self).get_context_data(**kwargs)

        context.update({
            'account': self.account,
            'card': self.account.get_credit_card,
            'bank_account': self.account.get_bank_account(verified=True),
        })

        return context

    def form_valid(self, form):
        charge_to = form.cleaned_data.get('charge_to')

        charge = form.save(commit=False)

        charge.account = self.account
        charge.created = timezone.now()
        charge.created_by = self.request.user

        if charge_to == 'card':
            card = self.account.get_credit_card()
            try:
                charge = card.charge(charge.amount, charge.description, self.request.user)
                charge.send_receipt_email()
                self.account.update_braintree_customer()
            except Exception, e:
                form.add_error(None, e.message)
                return self.form_invalid(form)
        elif charge_to == 'bank':
            bank_account = self.account.get_bank_account(verified=True)
            charge = bank_account.charge(charge.amount, charge.description, self.request.user)
            charge.send_receipt_email()
        elif charge_to == 'manual':
            charge.captured = True
            charge.paid = True
            charge.save()
            charge.send_receipt_email()

        pay_path = self.request.session.get('pay_path', None)

        if pay_path:
            del self.request.session['pay_path']
            return HttpResponseRedirect(pay_path)

        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse('admin_account_charges', args=(self.kwargs.get('pk'),))


class AccountChargeDetailView(StaffRequiredMixin, PermissionRequiredMixin, DetailView):
    """
    A view to see the details for a charge and issue a refund
    """

    permission_required = 'accounts.can_view_members'
    model = Charge
    template_name = 'admin/accounts/charge_detail.html'


class AccountChargeRefundFormView(StaffRequiredMixin, PermissionRequiredMixin, FormView):
    """
    A view to refund a charge
    """

    permission_required = 'accounts.can_edit_members'
    template_name = 'admin/accounts/charge_refund.html'
    form_class = RefundChargeForm

    @cached_property
    def charge(self):
        return Charge.objects.select_related('account').get(id=self.kwargs.get('pk'))

    def get_form_kwargs(self):
        kwargs = super(AccountChargeRefundFormView, self).get_form_kwargs()
        kwargs.update({
            'charge': self.charge,
        })
        return kwargs

    def get_context_data(self, **kwargs):
        context = super(AccountChargeRefundFormView, self).get_context_data(**kwargs)
        context.update({
            'charge': self.charge,
        })
        return context

    def form_valid(self, form):
        charge = self.charge
        refund_amount = form.cleaned_data.get('amount')
        description = form.cleaned_data.get('description')

        charge.refund(refund_amount, description, self.request.user)

        if charge.is_manual():
            messages.info(self.request, 'Note: This is a manual charge so you will have to manually refund this amount.')

        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse('admin_account_charge', args=(self.charge.account_id, self.charge.id))


class AccountChargeVoidFormView(StaffRequiredMixin, PermissionRequiredMixin, FormView):
    """
    A view to void a charge
    """

    permission_required = 'accounts.can_edit_members'
    template_name = 'admin/accounts/charge_void.html'
    form_class = VoidChargeForm

    @cached_property
    def charge(self):
        return Charge.objects.select_related('account').get(id=self.kwargs.get('pk'))

    def get_context_data(self, **kwargs):
        context = super(AccountChargeVoidFormView, self).get_context_data(**kwargs)
        context.update({
            'charge': self.charge,
        })
        return context

    def form_valid(self, form):
        charge = self.charge

        description = form.cleaned_data.get('description')

        try:
            charge.void(description, self.request.user)
        except Exception, e:
            form.add_error(None, e.message)
            return self.form_invalid(form)

        if charge.is_manual():
            messages.info(self.request, 'Note: This is a manual charge so you will have to manually refund this amount.')

        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse('admin_account_charge', args=(self.charge.account_id, self.charge.id))


class AccountReservationListView(StaffRequiredMixin, PermissionRequiredMixin, ListView):
    """
    A view to display all flight reservations for an account
    """

    permission_required = 'accounts.can_view_members'
    model = FlightReservation
    template_name = 'admin/accounts/flightreservation_list.html'

    def get_queryset(self):
        return FlightReservation.objects.filter(
            reservation__account__id=self.kwargs.get('pk')
        ).order_by('flight__departure')

    def get_context_data(self, **kwargs):
        context = super(AccountReservationListView, self).get_context_data(**kwargs)

        context.update({
            'account': Account.objects.get(pk=self.kwargs.get('pk'))
        })

        return context


class AccountSendOnboardingEmailView(StaffRequiredMixin, PermissionRequiredMixin, SingleObjectMixin, View):
    """
    Sends the account an onboarding email
    """

    permission_required = 'accounts.can_edit_members'
    model = Account

    def get(self, request, *args, **kwargs):
        account = self.get_object()
        user = account.primary_user

        if user is not None:
            user.send_onboarding_email()
            messages.info(request, 'Onboarding email sent to %s at %s' % (user.get_full_name(), user.email))
        elif account.get_first_user is not None:
            messages.info(request, 'Please select a primary user for the account %s' % (account))
            return redirect('admin_account_edit', account.pk)
        else:
            messages.info(request, 'Please create a user for the account %s' % (account))
            return redirect('admin_account_add_user', account.pk)

        return redirect('admin_account', account.pk)


class UserSendWelcomeEmailView(StaffRequiredMixin, PermissionRequiredMixin, SingleObjectMixin, View):
    """
    Sends the account an onboarding email
    """

    permission_required = 'accounts.can_edit_members'
    model = User

    def get(self, request, *args, **kwargs):
        user = self.get_object()
        user.send_welcome_email()

        messages.info(request, 'Welcome email sent to %s at %s' % (user.get_full_name(), user.email))

        return redirect('admin_account_user', user.account_id, user.userprofile.id)


class UserResetPasswordView(StaffRequiredMixin, PermissionRequiredMixin, SingleObjectMixin, View):
    """
    Sends the user an email to reset their password
    """

    permission_required = 'accounts.can_reset_user_password'
    model = User

    def get(self, request, *args, **kwargs):
        user = self.get_object()
        context = {
            'email': user.email,
            'uid': urlsafe_base64_encode(force_bytes(user.pk)),
            'user': user,
            'token': default_token_generator.make_token(user),
        }
        subject = 'Rise Password Reset'
        send_html_email('emails/password_reset', context, subject, settings.DEFAULT_FROM_EMAIL, [user.email])

        messages.info(request, 'Password reset email sent to %s at %s' % (user.get_full_name(), user.email))

        return redirect('admin_account_user', user.account_id, user.userprofile.id)


class UserUpdatePasswordView(StaffRequiredMixin, PermissionRequiredMixin, SingleObjectMixin, FormView):
    """
    A view to update a user's password.
    """

    permission_required = 'accounts.can_reset_user_password'
    model = User
    template_name = 'admin/accounts/user_update_password.html'
    form_class = UserPasswordForm

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super(UserUpdatePasswordView, self).dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        user = self.get_object()
        new_password1 = form.cleaned_data.get("new_password1")
        new_password2 = form.cleaned_data.get("new_password2")

        if new_password1 and new_password1 == new_password2:
            user.set_password(new_password1)
            user.save()
            messages.info(self.request, 'Password reset for %s' % user)
        else:
            messages.error(self.request, 'Passwords do not match')

        return redirect('admin_account_user', user.account_id, user.userprofile.id)


class AccountInvitationView(StaffRequiredMixin, PermissionRequiredMixin, SingleObjectMixin, FormView):
    """
    A view to allow an admin to view invitation deatils for a given account, issue more invites, link physical invites
    """

    permission_required = 'accounts.can_edit_members'
    model = Account
    template_name = 'admin/accounts/invitations.html'
    form_class = InvitationForm

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super(AccountInvitationView, self).dispatch(request, *args, **kwargs)

    def get_initial(self):
        initial = super(AccountInvitationView, self).get_initial()

        initial.update({
            'invites': self.object.invites,
        })

        return initial

    def get_context_data(self, **kwargs):
        context = super(AccountInvitationView, self).get_context_data(**kwargs)
        context.update({
            'account': self.object,
        })
        return context

    def form_valid(self, form):
        account = self.object
        invites = form.cleaned_data.get('invites')
        Account.objects.filter(id=account.id).update(invites=invites)

        code = form.cleaned_data.get('code')
        if code:
            Invite.objects.filter(code__istartswith=code, invite_type=Invite.INVITE_TYPE_PHYSICAL).update(account=account)

        return redirect('admin_account_invitations', account.pk)


class ExportOverfullAccountsView(StaffRequiredMixin, PermissionRequiredMixin, View):
    """
    A view to export accounts that have more members than paid members.
    """
    permission_required = 'accounts.can_view_members'

    def get(self, request, *args, **kwargs):
        accounts = Account.objects.exclude(status='C').all().select_related('plan')

        date_format = 'YYYY-MM-DD HH:mm:ss ZZ'

        # Create the HttpResponse object with the appropriate CSV header.
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="overfull_accounts.csv"'

        writer = unicodecsv.writer(response)
        writer.writerow(['Account ID', 'Account Name', 'Type',  'Status', 'Date Activated', 'Plan',
            '# of onboarding fees paid', 'Total Member User Count (all non-companion, non-coordinator-only)', 'Active Flying Member Count', 'Coordinator-Only Count (non-flying)', 'Companion Count'])

        for account in accounts:
            usercount = account.total_flying_members_count()
            if usercount > account.member_count:

                writer.writerow([
                    str(account.id),
                    account.account_name(),
                    account.get_account_type_display(),
                    account.get_status_display(),
                    arrow.get(account.activated).format(date_format) if account.activated else '',
                    'Corporate' if account.is_corporate() else str(account.plan),
                    str(account.member_count),
                    str(usercount),
                    str(account.active_flying_members_count()),
                    str(account.get_coordinator_count()),
                    str(account.get_companion_count())
                ])

        return response


class ExportAccountsView(StaffRequiredMixin, PermissionRequiredMixin, View):
    """
    A view to export accounts to CSV
    """

    permission_required = 'accounts.can_view_members'

    def get(self, request, *args, **kwargs):
        accounts = Account.objects.all().select_related('plan')
        sub_accounts = Subscription.objects.filter(status='active',account=accounts).values('account_id','amount')
        subamount_dict={}
        for key in sub_accounts:
            subamount_dict[key.get('account_id')]=key.get('amount')
        date_format = 'YYYY-MM-DD HH:mm:ss ZZ'

        # Create the HttpResponse object with the appropriate CSV header.
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="accounts.csv"'

        writer = unicodecsv.writer(response)
        writer.writerow(['Account ID', 'Account Name', 'Type', 'Founder', 'VIP', 'Status', 'Date Activated', 'Plan',
            'Member Count', 'Pass Count', 'Companion Pass Count', 'Amount', 'Payment Method', 'On-boarding Fee Paid',
            'Available Passes', 'Available Companion Passes', 'Complimentary Passes', 'Complimentary Companion Passes',
            'Stripe Customer Id', 'Braintree Customer Id', 'Flight Reservation Count', 'Cancelled Flight Reservations', 'Passenger Count'])

        for account in accounts:
            flight_reservation_count = FlightReservation.objects.filter(reservation__account=account, status__in=[FlightReservation.STATUS_RESERVED, FlightReservation.STATUS_CHECKED_IN, FlightReservation.STATUS_COMPLETE]).count()
            cancelled_flight_reservation_count = FlightReservation.objects.filter(reservation__account=account, status__in=[FlightReservation.STATUS_CANCELLED]).count()
            passenger_count = FlightReservation.objects.filter(reservation__account=account, status__in=[FlightReservation.STATUS_RESERVED, FlightReservation.STATUS_CHECKED_IN, FlightReservation.STATUS_COMPLETE]).aggregate(passenger_count=Sum('passenger_count')).get('passenger_count') or 0
            sub_amount = 0
            if account.do_not_charge:
                sub_amount = 0
            elif account.corporate_amount:
                sub_amount = str(account.corporate_amount)
            elif account.plan and subamount_dict.get(account.id) is not None:
                sub_amount = subamount_dict.get(account.id)
            writer.writerow([
                str(account.id),
                account.account_name(),
                account.get_account_type_display(),
                'Yes' if account.founder else 'No',
                'Yes' if account.vip else 'No',
                account.get_status_display(),
                arrow.get(account.activated).format(date_format) if account.activated else '',
                'Corporate' if account.is_corporate() else str(account.plan),
                str(account.member_count),
                str(account.pass_count),
                str(account.companion_pass_count),
                sub_amount,
                account.get_payment_method_display(),
                'Yes' if account.onboarding_fee_paid else 'No',
                str(account.available_passes),
                str(account.available_companion_passes),
                str(account.complimentary_passes),
                str(account.complimentary_companion_passes),
                account.stripe_customer_id,
                account.braintree_customer_id,
                str(flight_reservation_count),
                str(cancelled_flight_reservation_count),
                str(passenger_count),
            ])

        return response


class ExportUsersView(StaffRequiredMixin, PermissionRequiredMixin, View):
    """
    A view to export accounts to CSV
    """

    permission_required = 'accounts.can_view_members'

    def get(self, request, *args, **kwargs):
        userprofiles = UserProfile.objects.all().select_related('account', 'user').order_by('account', 'last_name', 'first_name')

        date_format = 'YYYY-MM-DD HH:mm:ss ZZ'

        # Create the HttpResponse object with the appropriate CSV header.
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="users.csv"'

        writer = unicodecsv.writer(response)
        writer.writerow(['Account ID', 'Account Name', 'User Name', 'Email', 'Staff', 'Active', 'Date Joined', 'Roles',
        'Can Fly', 'Origin Airport', 'Title', 'Date of Birth', 'Weight', 'Phone', 'Mobile Phone', 'Can Log In'])

        for user in userprofiles:
            login = user.user
            if not login:
                login = User()
                date_joined = 'N/A'
                has_login = 'No'
                groups = 'None'
                can_fly = 'Yes' #must be a companion in the new system
                is_staff= False
                is_active = False
            else:
                has_login = 'Yes'
                date_joined = login.date_joined
                groups = ', '.join(login.groups.all().values_list('name', flat=True))
                can_fly = login.can_fly()
                is_staff = login.is_staff
                is_active = login.is_active

            writer.writerow([
                str(user.account.id) if user.account else '',
                user.account.account_name() if user.account else '',
                user.get_full_name(),
                user.email,
                'Yes' if is_staff else 'No',
                'Yes' if is_active else 'No',
                date_joined if date_joined == 'N/A' else arrow.get(date_joined).format(date_format),
                groups,
                can_fly,
                str(user.origin_airport),
                user.title ,
                arrow.get(user.date_of_birth).format(date_format) if user.date_of_birth else '',
                user.get_weight_display(),
                user.phone,
                user.mobile_phone,
                has_login
            ])

        return response


class ExportInvitesView(StaffRequiredMixin, PermissionRequiredMixin, View):
    """
    A view to export accounts to CSV
    """

    permission_required = 'accounts.can_view_members'

    def get(self, request, *args, **kwargs):
        invites = Invite.objects.all().select_related()

        date_format = 'YYYY-MM-DD HH:mm:ss ZZ'

        # Create the HttpResponse object with the appropriate CSV header.
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="invites.csv"'

        writer = unicodecsv.writer(response)
        writer.writerow(['Account ID', 'Account Name', 'Invite Code', 'Invite Type', 'Created On', 'Created By',
                         'Redeemed', 'Redeemed On', 'Redeemed By', 'First Name', 'Last Name', 'Email', 'Phone'])

        for invite in invites:
            writer.writerow([
                str(invite.account.id) if invite.account else '',
                invite.account.account_name() if invite.account else '',
                invite.code,
                invite.get_invite_type_display(),
                arrow.get(invite.created_on).format(date_format),
                invite.created_by.get_full_name() if invite.created_by else '',
                'Yes' if invite.redeemed else 'No',
                arrow.get(invite.redeemed_on).format(date_format) if invite.redeemed_on else '',
                invite.redeemed_by.get_full_name() if invite.redeemed_by else '',
                invite.first_name or '',
                invite.last_name or '',
                invite.email or '',
                invite.phone or '',
            ])

        return response


class OnCallScheduleCreateView(StaffRequiredMixin, PermissionRequiredMixin, FormView):
    """
    A view to add a oncall schedule
    """

    permission_required = 'accounts.can_manage_staff'
    template_name = 'admin/accounts/oncall_schedule_user_form.html'
    form_class = OnCallScheduleForm

    def form_valid(self, form):
        oncallSchedule = OncallSchedule()
        oncallSchedule.user = form.cleaned_data.get('user')
        oncallSchedule.airport = form.cleaned_data.get('airport')
        startHour = form.cleaned_data.get('startHour')
        endHour = form.cleaned_data.get('endHour')
        oncallSchedule.start_date = form.cleaned_data.get('start_date') + timedelta(hours=int(startHour))
        oncallSchedule.end_date = form.cleaned_data.get('end_date') + timedelta(hours=int(endHour))
        flight_list = self.request.POST.getlist('flights')
        oncallSchedule.save()
        if flight_list is not None and len(flight_list)>0:
            flights = Flight.objects.filter(id__in=flight_list).all()
            for flight in flights:
                oncallSchedule.flights.add(flight)
            oncallSchedule.save()
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse('admin_oncall_schedule')


class OnCallScheduleView(StaffRequiredMixin, PermissionRequiredMixin, ListView):

    permission_required = 'accounts.can_manage_staff'
    model = OncallSchedule
    template_name = 'admin/accounts/oncall_schedule.html'

    def get_context_data(self, **kwargs):
        context = super(OnCallScheduleView, self).get_context_data(**kwargs)

        list = OncallSchedule.objects.all()
        context.update({
            'sorted_list': list
        })

        return context


class OnCallScheduleDeleteView(StaffRequiredMixin, PermissionRequiredMixin, View):
    """
    Admin view to delete a oncall schedule
    """
    permission_required = 'accounts.can_manage_staff'

    def get(self, request, *args, **kwargs):
        oncall = OncallSchedule.objects.filter(id=self.kwargs.get('pk', None))
        if oncall:
            oncall.delete()
        return redirect('admin_oncall_schedule')


class OriginCityFlights(View):
    def get(self, request, *args, **kwargs):
        origin_city = request.GET.get('city')
        start_date = request.GET.get('startdate')
        end_date = request.GET.get('enddate')
        startdate = datetime.datetime.strptime(start_date,'%b %d, %Y')
        enddate = datetime.datetime.strptime(end_date,'%b %d, %Y')
        starthour = request.GET.get('starthour')
        endhour = request.GET.get('endhour')
        startdate = startdate + timedelta(hours=int(starthour))
        enddate = enddate + timedelta(hours=int(endhour))
        flight_list = Flight.objects.filter(origin_id=origin_city,flight_type=Flight.TYPE_REGULAR,departure__gte=startdate,departure__lte=enddate).all()
        choicelist=[]
        if flight_list is not None:
            for flight in flight_list:
                val = [flight.id, flight.__str__()]
                choicelist.append(val)
        json_result = json.dumps(choicelist)
        return HttpResponse(json_result, content_type='application/json')
