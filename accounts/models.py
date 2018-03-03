import pytz
from django.db import models, transaction
from django.conf import settings
from django.db.models import Q, Sum
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, Permission
from django.utils import timezone
from django.utils.functional import cached_property
from django.core.signing import Signer
from django.core.urlresolvers import reverse
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from dateutil.relativedelta import relativedelta

from auditlog.registry import auditlog
import arrow
import datetime
import stripe
import redis
import urllib
import hashlib
import braintree
from datetime import date, timedelta
from imagekit.models import ImageSpecField
from imagekit.processors import Transpose, ResizeToFill
from localflavor.us.models import PhoneNumberField, USStateField

from htmlmailer.mailer import send_html_email
from decimal import Decimal, ROUND_HALF_UP

from .tokens import invite_token_generator
from reservations.models import FlightReservation, Reservation
from .managers import UserManager, InviteManager, PaymentMethodManager


stripe.api_key = settings.STRIPE_API_KEY


class Account(models.Model):
    """
    An account can have 1 or more users. Those users share the account resources of the membership tier.

    founder: True if this is a founding account
    vip: VIP flag

    preferred_cities: This account's preferred citites for travel
    invites: The number of invites remaining for this account
    origin_city: The city which this account will primarily fly out of

    status: The status of this account
    activated: When this account was originally activated for the purpose of determining when this account can be
        cancelled

    plan: Which plan this account is subscribed to  Note:  There needs to be a $0 plan for RA only members not the same
        as a trial.
        Eventually there may be a breakout for members to be both RA at one or the other levels + regular RISE.


    company_name: Optional name of the company for this account
    account_type: The type of account, either corporate or individual
    corporate_amount: The amount per month for this account if corporate
    payment_method: For corporate accounts, some may want to pay via a check or wire transfer instead of using a credit
        card via Stripe.
    member_count: The number of members that are allowed to fly on this account. More for corporate accounts than
        individual accounts.

    pass_count: The number of save my seat passes for this account as per the account's current plan.
    companinon_pass_count: The number of companion passes for this account as per the account's current plan.

    available_passes: The number of passes that are currently available for this account to use. This value will be
        incremented or decremented as the users book/complete flights.
    available_companion_passes: The number of companion passes available for free. This value only decrements with use
        and is reset at the beginning of the billing cycle.
    complimentary_passes: Comp passes added to an account by an admin. These will be used prior to the available passes.
        This value only decrements and carries over between billing cycles.
    complimentary_companion_passes: Comp companion passes added to an account by admin. This passes will be used prior
        to the available_companion_passes value. This passes carry over between billing cycles and only decrement on use.

    onboarding_fee_paid: Status of the payment for the account's onboarding fees such as deposit charges for team
        member slots
    """

    TYPE_INDIVIDUAL = 'I'
    TYPE_CORPORATE = 'C'

    ACCOUNT_TYPE_CHOICES = (
        (TYPE_INDIVIDUAL, 'Individual'),
        (TYPE_CORPORATE, 'Corporate'),
    )

    PAYMENT_CREDIT_CARD = 'C'
    PAYMENT_MANUAL = 'M'
    PAYMENT_ACH = 'A'

    PAYMENT_CHOICES = (
        (PAYMENT_CREDIT_CARD, 'Credit Card'),
        (PAYMENT_ACH, 'ACH'),
        (PAYMENT_MANUAL, 'Manual'),
    )

    STATUS_PENDING = 'P'
    STATUS_PENDING_ACH = 'V'  # V for verify ACH account
    STATUS_ACTIVE = 'A'
    STATUS_SUSPENDED = 'S'
    STATUS_DELINQUENT = 'D'
    STATUS_CANCELLED = 'C'

    STATUS_CHOICES = (
        (STATUS_PENDING, 'Pending'),
        (STATUS_ACTIVE, 'Active'),
        (STATUS_SUSPENDED, 'Suspended'),
        # (STATUS_DELINQUENT, 'Delinquent'),
        (STATUS_PENDING_ACH, 'Pending ACH Verification'),
        (STATUS_CANCELLED, 'Cancelled'),
    )

    founder = models.BooleanField(default=False)
    vip = models.BooleanField(default=False)

    preferred_cities = models.ManyToManyField('accounts.City', blank=True)
    invites = models.PositiveIntegerField(default=0)
    origin_city = models.ForeignKey('accounts.City', null=True, related_name='members')

    status = models.CharField(max_length=1, choices=STATUS_CHOICES, default=STATUS_PENDING)
    activated = models.DateTimeField(blank=True, null=True)

    plan = models.ForeignKey('billing.Plan', null=True, blank=True, on_delete=models.SET_NULL)
    contract = models.ForeignKey('billing.PlanContractPrice', null=True, blank=True, on_delete=models.SET_NULL)
    contract_start_date = models.DateTimeField(blank=True, null=True)
    contract_end_date = models.DateTimeField(blank=True, null=True)
    contract_signature = models.CharField(max_length=50, blank=True, null=True)
    contract_signeddate = models.DateTimeField(blank=True, null=True)
    do_not_renew = models.BooleanField(default=False)
    company_name = models.CharField(max_length=128, blank=True, null=True)
    primary_user = models.ForeignKey('accounts.User', related_name='primary_members', default=None, null=True)
    primary_profile = models.ForeignKey('accounts.UserProfile', related_name='primary_profiles', default=None, null=True)
    account_type = models.CharField(max_length=1, default=TYPE_INDIVIDUAL, choices=ACCOUNT_TYPE_CHOICES)
    corporate_amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    payment_method = models.CharField(max_length=1, default=PAYMENT_CREDIT_CARD, choices=PAYMENT_CHOICES)
    member_count = models.PositiveIntegerField(default=1)
    pass_count = models.PositiveIntegerField(default=2)
    companion_pass_count = models.PositiveIntegerField(default=2)

    available_passes = models.IntegerField(default=0)
    available_companion_passes = models.IntegerField(default=0)
    complimentary_passes = models.IntegerField(default=0)
    complimentary_companion_passes = models.IntegerField(default=0)

    onboarding_fee_paid = models.BooleanField(default=False)

    stripe_customer_id = models.CharField(max_length=64, blank=True, null=True)
    braintree_customer_id = models.CharField(max_length=64, blank=True, null=True)

    do_not_charge = models.BooleanField(default=False)

    @property
    def has_unsigned_contract(self):
        if self.contract_id and not self.contract_signeddate:
            return True
        return False

    def account_name(self):
        """
        Returns the name for this account.

        If corporate, company name

        If individual, primary member's name
        """
        if self.is_corporate() and self.company_name is not None:
            return self.company_name

        primary = self.primary_user
        if primary is not None:
            return primary.get_full_name()
        elif self.get_first_user:
            first_user = self.get_first_user
            return first_user.get_full_name()

        return 'Account %s' % (self.pk)

    def get_cache_key(self, name):
        """
        Returns a cache key for the given name.

        THE NAME SHOULD MATCH THE FIELD NAME OF THE VALUE BEING CACHED.
        """
        return 'account-%d-%s' % (self.pk, name)

    def refresh_cache(self):
        """
        refreshes the cache for a list of fields
        """
        r = redis.from_url(settings.REDIS_URL)

        fields = ['available_passes', 'available_companion_passes', 'complimentary_passes', 'complimentary_companion_passes']

        for field in fields:
            cache_key = self.get_cache_key(field)
            value = getattr(self, field)
            r.set(cache_key, value)



    def has_valid_payment_method(self):
        # todo: verify this logic

        if self.is_credit_card():
            return True
        elif self.is_ach():
            if not self.need_verify_bank_account():
                return True
        return False

    def has_any_payment_method(self):
        # payment method on account gets set to C by default even if no CC so have to check for existence of card too)
        if not self.is_ach() and not self.is_credit_card() and not self.is_manual():
            return False
        return True

    def has_braintree(self):
        """
        Returns True if this account has a braintree customer setup
        """
        return self.braintree_customer_id not in (None, '')

    def has_stripe(self):
        """
        Returns True if this account has a stripe customer setup
        """
        return self.stripe_customer_id not in (None, '')

    def is_anywhere_only(self):
        """
        Returns True if the billing.Plan associated with this account has anywhere_only = true

        """
        if self.plan:
            return self.plan.anywhere_only
        return False

    def total_available_passes(self):
        """
        Returns the total number of passes available

        FOR DISPLAY ONLY since it limits to 0
        """
        total = self.available_passes + self.complimentary_passes
        if total < 0:
            return 0
        return total

    def total_available_companion_passes(self):
        """
        Returns the total number of companion passes available

        FOR DISPLAY ONLY since it limits to 0
        """
        total = self.available_companion_passes + self.complimentary_companion_passes
        if total < 0:
            return 0
        return total

    def charge(self, amount, description, user):
        """
        Charge the accounts selected payment method the given amount
        """
        if amount <= 0 or self.is_manual():
            from billing.models import Charge
            return Charge.objects.create(
                account=self,
                payment_method=Charge.PAYMENT_METHOD_MANUAL,
                amount=amount,
                description=description,
                captured=True,
                paid=True,
                status='success',
                created=timezone.now(),
                created_by=user,
            )
        from billing.models import Card,BankAccount

        billing_payment_method = BillingPaymentMethod.objects.filter(account=self.id,is_default=True).first()
        #if the bank account is not verified
        if billing_payment_method is not None and billing_payment_method.payment_method == BillingPaymentMethod.PAYMENT_ACH and BankAccount.objects.filter(billing_payment_method=billing_payment_method,verified=True).first() is None:
            billing_payment_method = None

        if billing_payment_method is not None:
            if billing_payment_method.payment_method == BillingPaymentMethod.PAYMENT_CREDIT_CARD:
                return Card.objects.filter(billing_payment_method=billing_payment_method).first().charge(amount, description, user)
            else:
                return BankAccount.objects.filter(billing_payment_method=billing_payment_method).first().charge(amount, description, user)
        elif self.is_credit_card():
            card = self.get_credit_card()
            return card.charge(amount, description, user)
        elif self.is_ach():
            bank_account = self.get_bank_account(verified=True)
            if bank_account is not None:
                return bank_account.charge(amount, description, user)
            else:
                return None

    def upgrade_anywherebasic_to_plus(self,user=None):
        """
        Changes plan from AnywhereBasic to Plus.  Doesn't use change_plan() beause there are no passes
        or initiation fees involved.

        If we plan to allow regular members to down-grade to Anywhere Plus that will be a different method.

        Returns:

        """
        if not self.plan or not self.plan.anywhere_only:
            from billing.models import InvalidUpgradeException
            raise InvalidUpgradeException("Only RISE ANYWHERE Limited memberships are upgraded to RISE ANYWHERE.")

        if self.plan.name == "RISE ANYWHERE":
            from billing.models import InvalidUpgradeException
            raise InvalidUpgradeException("Member is already a RISE ANYWHERE member.")

        inactive=False
        with transaction.atomic():
            from billing.models import Plan
            plan = Plan.objects.filter(name="RISE ANYWHERE").first()
            if not plan:
                raise ReferenceError("RISE ANYWHERE plan not found")
            self.plan = plan

            self.save()

            if self.has_valid_payment_method():
                subscription = self.get_subscription()
                if not subscription:
                    from billing.models import Subscription
                    Subscription.objects.create_subscription(self,created_by=user)
                else:
                    subscription.description = "{} Subscription".format(self.plan.name)
                    subscription.update_amount(self.plan.amount,user=user)
            else:
                inactive=True

        if inactive:
            from billing.models import IncompleteUpgradeException
            raise IncompleteUpgradeException("Your account is pending bank account verification.  Your subscription will start once your bank account is verified.")


    def change_plan(self, new_plan, force=False, contract=None,user=None):
        """
        Change's a individual user's plan to the new plan
        """
        from billing.models import InvalidUpgradeException

        if new_plan is None:
            raise InvalidUpgradeException("Plan is required.")
        # sanity check for same plan, do nothing
        if self.plan == new_plan and not force:
            return

        # if new plan is a contract plan, contract must be provided.
        if not contract and new_plan.requires_contract:
            raise InvalidUpgradeException("The Plan you have selected requires a Contract be selected.")

        with transaction.atomic():
            is_trial = self.is_trial()
            passes_in_use = self.passes_in_use()
            companion_passes_in_use = self.companion_passes_in_use()

            self.plan = new_plan
            self.pass_count = new_plan.pass_count
            self.companion_pass_count = new_plan.companion_passes
            self.contract = contract
            if self.contract:
                self.contract_start_date = datetime.datetime.now()
                # add 3, 6, 12 months etc to find the end date.
                self.contract_end_date = self.contract_start_date + relativedelta(months=self.contract.contract_length)
            else:
                self.contract_start_date = None
                self.contract_end_date = None

            self.available_passes = new_plan.pass_count - passes_in_use
            # TODO: cancel flights if not enough passes
            self.available_companion_passes = new_plan.companion_passes - companion_passes_in_use
            # TODO: cancel flights if not enough compasses

            if self.is_active():
                # if switching from a Trial account and the onboarding fee has not been paid yet
                onboarding_fee = self.get_onboarding_fee_total()
                if is_trial and not self.onboarding_fee_paid and onboarding_fee > 0:
                    if self.is_corporate():
                        description = 'Fee for %d team members ($%d/member) + %s tax' % (self.member_count, settings.DEPOSIT_COST, settings.DEPOSIT_TAX_PERCENT)
                    else:
                        description = 'Member initation fee'

                    charge = self.charge(onboarding_fee, description, user)
                    charge.send_receipt_email()
                    self.onboarding_fee_paid = True

            self.save()

            if self.is_active():
                subscription = self.get_subscription()
                # moved all the amount logic into new property to encapsulate contracts where needed
                amt = self.subscription_amount
                if amt:
                    if subscription is not None:
                        if not self.is_corporate():
                           subscription.description = "{} Subscription".format(self.plan.name)
                        subscription.update_amount(amt,user=user)
                    else:
                        from billing.models import Subscription
                        Subscription.objects.create_subscription(self,created_by=user)
                elif self.plan.anywhere_only and self.plan.amount == 0:
                    # this is actually valid.  there should not be a subscription in this case.
                    subscription.cancel(refund=False)
                else:
                    raise InvalidUpgradeException("There was an error determining the plan price.")


    @property
    def subscription_amount(self):
        '''
        Requires a contract + plan for independent regular accounts.
        Returns: Either the amount or null if there is not a valid
        contract

        '''
        if self.plan.anywhere_only:
            return self.plan.amount
        if self.is_corporate():
            return self.corporate_amount
        if self.contract:
            return self.contract.amount
        return None

    def get_subscription(self):
        """
        Returns the active subscriptions for this account
        """
        from billing.models import Subscription
        return next(iter(Subscription.objects.get_current_subscriptions(self)), None)

    def calculate_monthly_corporate_price(self):
        """
        Calculate monthly price for corporate members

        Base price of 2500 include 2 members and 1 set of passes
        """

        base_price = 3700
        pass_price = 925
        pass_threshold = 4

        return base_price + (self.pass_count - pass_threshold) * pass_price

    def upcoming_flight_reservations(self):
        """
        returns a queryset for upcoming flight reservations
        """
        start = arrow.now().floor('day')
        flight_reservations = FlightReservation.objects.filter(
            reservation__account=self,  # reservations for this account
            reservation__status=Reservation.STATUS_RESERVED,  # that have been reserved
            status__in=(FlightReservation.STATUS_RESERVED, FlightReservation.STATUS_CHECKED_IN),  # that are reserved or checked in
            flight__departure__gte=start.datetime
        )

        return flight_reservations

    def upcoming_flight_reservations_totals(self):
        """
        return totals for upcoming flight reservations
        """
        return self.upcoming_flight_reservations().aggregate(
            passenger_count=Sum('passenger_count'),
            pass_count=Sum('pass_count'),
            companion_pass_count=Sum('companion_pass_count'),
            complimentary_pass_count=Sum('complimentary_pass_count'),
            complimentary_companion_pass_count=Sum('complimentary_companion_pass_count'),
            buy_pass_count=Sum('buy_pass_count'),
            buy_companion_pass_count=Sum('buy_companion_pass_count'),
            cost=Sum('cost'),
        )

    def passes_in_use(self):
        """
        Returns the number of passes currently in use by flight reservations
        in pending, reserved, or checked-in status.
        """
        results = FlightReservation.objects.filter(status__in=[FlightReservation.STATUS_PENDING, FlightReservation.STATUS_RESERVED, FlightReservation.STATUS_CHECKED_IN], reservation__account=self).aggregate(pass_count=Sum('pass_count'))
        pass_count = results.get('pass_count', 0)
        if pass_count is None:
            return 0
        return pass_count

    def companion_passes_in_use(self):
        """
        Returns the number of companion passes currently in use by Flight reservations
        in pending, reserved, or checked-in status.
        """
        results = FlightReservation.objects.filter(status__in=[FlightReservation.STATUS_PENDING, FlightReservation.STATUS_RESERVED, FlightReservation.STATUS_CHECKED_IN], reservation__account=self).aggregate(companion_pass_count=Sum('companion_pass_count'))
        companion_pass_count = results.get('companion_pass_count', 0)
        if companion_pass_count is None:
            return 0
        return companion_pass_count

    def can_cancel(self):
        """
        Return's true if this account can be cancelled.

        Can only cancel after 90 days
        """
        if self.activated is None:
            return False

        if self.is_corporate():
            interval = 90
        else:
            interval = 30

        diff = date.today() - self.activated.date()
        return diff > timedelta(days=interval)

    def is_active(self):
        """
        Return true if this account is active
        """
        return self.status == Account.STATUS_ACTIVE

    def is_pending(self):
        """
        Return true if this account is pending
        """
        return self.status == Account.STATUS_PENDING

    def is_suspended(self):
        """
        Return true if this account is suspended
        """
        return self.status == Account.STATUS_SUSPENDED

    def is_pending_ach(self):
        """
        Return true if this account is pending ACH verification
        """
        return self.status == Account.STATUS_PENDING_ACH

    def is_corporate(self):
        """
        Returns true if this is a corporate account
        """
        return self.account_type == Account.TYPE_CORPORATE

    def is_credit_card(self):
        """
        Returns True if this account is paid with a credit card
        """
        credit_card = BillingPaymentMethod.objects.filter(account_id=self.id,payment_method=BillingPaymentMethod.PAYMENT_CREDIT_CARD).first()
        if credit_card is not None:
            return True
        else:
            return False

    def is_ach(self):
        """
        Returns True if this account is paid with a bank account
        """
        bank_account = BillingPaymentMethod.objects.filter(account_id=self.id,payment_method=BillingPaymentMethod.PAYMENT_ACH).first()
        if bank_account is not None:
            return True
        else:
            return False

    def is_manual(self):
        """
        Returns True if this account is paid manually
        """
        return self.payment_method == Account.PAYMENT_MANUAL

    def is_trial(self):
        """
        Return true if this account is a trial account
        """
        is_trial = False
        if self.is_corporate():
            is_trial = self.corporate_amount is None or self.corporate_amount == 0
        else:
            try:
                is_trial = self.plan.name == 'Trial'
            except:
                pass
        return is_trial

    def get_all_payment_methods(self):
        bill_pay_methods = BillingPaymentMethod.objects.filter(account=self).all()
        from billing.models import Card
        cards = Card.objects.filter(account=self).all()
        from billing.models import BankAccount
        bankaccounts = BankAccount.objects.filter(account=self,verified=True).all()
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
        return paylist

    def get_credit_card(self):
        """
        Returns the credit card associated with this account. Should only be 1 if any.
        """
        from billing.models import Card
        try:
            pay_method = BillingPaymentMethod.objects.filter(account_id=self.id,is_default=True,payment_method=BillingPaymentMethod.PAYMENT_CREDIT_CARD).first()
            if pay_method is not None:
                return Card.objects.filter(billing_payment_method_id=pay_method.id).first()
            else:
                pay_method = BillingPaymentMethod.objects.filter(account_id=self.id,payment_method=BillingPaymentMethod.PAYMENT_CREDIT_CARD).first()
                if pay_method is not None:
                    return Card.objects.filter(billing_payment_method_id=pay_method.id).first()
                else:
                    return None
        except Card.DoesNotExist:
            return None

    def get_default_payment(self):
        from billing.models import Card,BankAccount
        try:
            pay_method = BillingPaymentMethod.objects.filter(account_id=self.id,is_default=True).first()
            if pay_method is not None:
                if pay_method.payment_method == BillingPaymentMethod.PAYMENT_CREDIT_CARD:
                    return Card.objects.filter(billing_payment_method_id=pay_method.id).first()
                else:
                    bank_account = BankAccount.objects.filter(billing_payment_method_id=pay_method.id,verified=True).first()
                    if bank_account is not None:
                        return bank_account
            pay_method = BillingPaymentMethod.objects.filter(account_id=self.id,payment_method=BillingPaymentMethod.PAYMENT_CREDIT_CARD).first()
            if pay_method is not None:
                return Card.objects.filter(billing_payment_method_id=pay_method.id).first()
            else:
                pay_method_list = BillingPaymentMethod.objects.filter(account_id=self.id,payment_method=BillingPaymentMethod.PAYMENT_ACH)
                if pay_method_list is not None:
                    return BankAccount.objects.filter(billing_payment_method=pay_method_list,verified=True).first()
                else:
                    return None
        except Card.DoesNotExist:
            return None

    def get_all_credit_cards(self):
        """
        Returns the credit card associated with this account. Should only be 1 if any.
        """
        from billing.models import Card
        try:
            pay_methods = BillingPaymentMethod.objects.filter(account_id=self.id,payment_method=BillingPaymentMethod.PAYMENT_CREDIT_CARD).all()
            if pay_methods is not None:
                return Card.objects.filter(billing_payment_method__in=pay_methods).all()
        except Card.DoesNotExist:
            return None

    def need_verify_bank_account(self):
        """
        Return's true if this account needs to verify their bank account info
        """
        from billing.models import BankAccount
        return BankAccount.objects.filter(account=self, verified=False).exists()

    def get_bank_account(self,verified=False):
        """
        Returns the credit card associated with this account. Should only be 1 if any.
        """

        from billing.models import BankAccount
        try:
            pay_method = BillingPaymentMethod.objects.filter(account_id=self.id,is_default=True,payment_method=BillingPaymentMethod.PAYMENT_ACH).first()
            if pay_method is not None:
                if verified:
                    bank_account = BankAccount.objects.filter(billing_payment_method_id=pay_method.id,verified=True).first()
                else:
                    bank_account = BankAccount.objects.filter(billing_payment_method_id=pay_method.id).first()
                if bank_account is not None:
                    return bank_account
            pay_method_list = BillingPaymentMethod.objects.filter(account_id=self.id,payment_method=BillingPaymentMethod.PAYMENT_ACH).all()
            if pay_method_list is not None:
                if verified:
                    return BankAccount.objects.filter(billing_payment_method__in=pay_method_list,verified=True).first()
                else:
                    return BankAccount.objects.filter(billing_payment_method__in=pay_method_list).first()
            else:
                return None
        except BankAccount.DoesNotExist:
            return None

    def get_all_bank_account(self):
        """
        Return all the bank accounts associated with this account.
        """
        from billing.models import BankAccount
        try:
            pay_methods = BillingPaymentMethod.objects.filter(account_id=self.id,payment_method=BillingPaymentMethod.PAYMENT_ACH).all()
            if pay_methods is not None:
                return BankAccount.objects.filter(billing_payment_method__in=pay_methods).all()
        except BankAccount.DoesNotExist:
            return None

    def get_monthly_amount(self):
        """
        Returns the monthly subscription amount
        """
        if self.is_corporate():
            return self.corporate_amount
        elif self.plan:
            return self.plan.amount
        return None

    def get_stripe_customer(self):
        """
        Returns the stripe customer object for this account
        """
        if self.stripe_customer_id is None:
            return None

        return stripe.Customer.retrieve(self.stripe_customer_id)

    def get_onboarding_fee(self):
        """
        Returns the onboarding fee for this account. Corporate is DEPOSIT_COST * member count and individual is flat DEPOSIT_COST.

        If the corporate account amount is 0 or plan amount is 0, no onboarding fee.
        """
        if self.is_corporate():
            if self.corporate_amount == 0:
                return 0
            else:
                return settings.DEPOSIT_COST * self.member_count
        else:
            if self.plan and not self.plan.has_onboarding:
                return 0
            else:
                return settings.DEPOSIT_COST

    def get_onboarding_fee_tax(self, tax_rate=settings.DEPOSIT_TAX):
        return (self.get_onboarding_fee() * tax_rate).quantize(Decimal('0.00'), rounding=ROUND_HALF_UP)

    def get_onboarding_fee_total(self):
        return (self.get_onboarding_fee() + self.get_onboarding_fee_tax())

    def get_one_onboarding_fee_total(self):
        return ((settings.DEPOSIT_COST * settings.DEPOSIT_TAX) + settings.DEPOSIT_COST).quantize(Decimal('0.00'), rounding=ROUND_HALF_UP)

    @cached_property
    def get_first_user(self):
        """
        Returns the first user for this account.
        """
        return next(iter(self.user_set.all().order_by('id').select_related('userprofile')), None)

    def get_members(self):
        """
        Returns queryset for team members for this account
        """
        return User.objects.filter(account=self, is_active=True).select_related('account')

    def get_member_profiles(self, active_only=True):
        """
        Replacement for get_members based on profile
        Returns:

        """
        if active_only:
            userIds =  User.objects.filter(account=self, is_active=True).exclude(groups__name='Companion').select_related('account').values_list("id", flat=True)
        else:
            userIds =  User.objects.filter(account=self).exclude(groups__name='Companion').select_related('account').values_list("id", flat=True)
        profiles = UserProfile.objects.filter(Q(user__id__in=userIds) | (Q(account__id=self.id) & Q(user__id__isnull=True)))
        return profiles

    def get_all_member_profiles(self):
        return self.get_member_profiles(False)

    def get_member_count(self):
        """
        Returns count of team members for this account
        """
        return User.objects.filter(account=self, is_active=True).select_related('account').count()

    def get_companions(self):
        """
        Returns queryset for companions for this account
        """
        return User.objects.filter(groups__name='Companion', account=self, is_active=True).select_related('account')

    def get_companion_profiles(self):
        """replacement for get_companions based on profile
        """
        companionUserIds =  User.objects.filter(groups__name='Companion', account=self, is_active=True).select_related('account').values_list("id", flat=True)
        profiles = UserProfile.objects.filter(Q(user__id__in=companionUserIds) | (Q(account__id=self.id) & Q(user__id__isnull=True)))
        return profiles

    def get_companion_count(self):
        """
        Returns count of companions for this account
        """
        return User.objects.filter(groups__name='Companion', account=self, is_active=True).count()

    def get_coordinator_count(self):
        """

        Returns: users who are only coordinators, i.e. don't fly

        """
        users = User.objects.filter(groups__name='Coordinator', account=self, is_active=True).all()
        count = 0
        for user in users:
            # we only want users who are ONLY coordinators.
            if user.groups.count() == 1:
                count+=1
        return count

    def get_flying_members(self):
        """
        Returns the number of users on this account with the "can_fly" permission
        """
        perm = Permission.objects.get(codename='can_fly')
        return User.objects.filter(Q(groups__permissions=perm) | Q(user_permissions=perm), account=self, is_active=True).distinct()

    def flying_member_count(self):
        """
        Returns the number of users on this account with the "can_fly" permission
        AMF:  This is bad logic.  It doesn't exclude companions or coordinators, and only looks at active leaving
        a loophole to not pay onboarding for new members.  Use total_flying_members_count instead.
        """
        perm = Permission.objects.get(codename='can_fly')
        return User.objects.filter(Q(groups__permissions=perm) | Q(user_permissions=perm), account=self, is_active=True).distinct().count()

    def active_flying_members_count(self):
        """
        Number of currently active members with flying privileges.  Excludes companions accounts.
        Returns:

        """
        users =  User.objects.filter(account=self, is_active=True).exclude(Q(groups__name='Companion')).distinct()
        flying_members = []
        for user in users:
            if user.has_perm('accounts.can_fly'):
                flying_members.append(user)
        return flying_members.__len__()


    def total_flying_members_count(self):
        """
        Returns the total number of members that have ever been added to this account for purposes
        of counting whether adding a new member will require onboarding charges.
        Does NOT include companions, also does NOT include coordinators that don't also have fly permissions.
        DOES include inactive users.

        Returns: integer

        """
        users =  User.objects.filter(account=self).exclude(Q(groups__name='Companion')).distinct()
        flying_members = []
        for user in users:
            if not user.has_perm('accounts.can_fly'):
                coord = user.groups.filter(name='Coordinator').first()
                if not coord:
                    flying_members.append(user)
            else:
                flying_members.append(user)
        return flying_members.__len__()

    def is_full(self):
        """
        Checks number of active users against member_count
        """
        return self.total_flying_members_count() >= self.member_count

    def set_suspended(self):
        """
        Sets the account status to suspended
        """
        self.status == Account.STATUS_SUSPENDED
        self.save()
        for reservation in self.reservation_set.all():
            reservation.cancel()
        self.refresh_cache()

    def send_add_member_payment_failed_email(self, member, addedBy, isAdd=True):
        """

        When adding a new flying member member to account, if payment fails email goes to internal list

        """
        subject = 'Add Member to Account payment failure'

        if isAdd:
            msg = 'This account either added a new member, but the onboarding charge failed.'
        else:
            msg = 'This account added flying privileges to an existing coordinator, but the onboarding charge failed.'

        context = {
            'account': self,
            'error_message': msg,
            'addedbyname': addedBy.get_full_name(),
            'membername': member.get_full_name()
        }

        send_html_email('emails/admin_addmember_payment_failed_notification', context, subject, settings.DEFAULT_FROM_EMAIL, settings.PAYMENT_FAILED_NOTIFICATION_LIST)


    def send_welcome_anywhere_email(self):
        """

        Send a welcome email to RiseAnywhere Ltd members.

        """
        subject = 'Welcome to RISE ANYWHERE!'

        user = self.primary_user

        context = {
            'user': user,
            'user_profile': next(iter(UserProfile.objects.filter(user=user).select_related()), None),
        }

        send_html_email('emails/welcome_anywhere', context, subject, settings.DEFAULT_FROM_EMAIL, [user.email])

    def send_admin_signup_email(self):
        """
        Sends an email to Rise alerting them of a sign up
        """
        subject = 'New Account Sign Up'

        context = {
            'account': self,
        }

        send_html_email('emails/admin_account_signup', context, subject, settings.DEFAULT_FROM_EMAIL, settings.SIGNUP_NOTIFICATION_LIST)

    def send_admin_anywhere_signup_email(self):
        """
        Sends an email to Rise alerting them of a sign up
        """
        subject = 'New RiseAnywhere Account Sign Up'

        context = {
            'account': self,
        }

        send_html_email('emails/admin_anywhere_account_signup', context, subject, settings.ANYWHERE_FROM_EMAIL, settings.ANYWHERE_SIGNUP_NOTIFICATION_LIST)

    def update_braintree_customer(self):
        """
        Update Braintree customer data for account

        Returns the Customer object or none
        """
        if self.has_braintree():
            first_name = ''
            last_name = ''
            email = ''
            user = self.primary_user
            if user:
                first_name = user.first_name
                last_name = user.last_name
                email = user.email

            result = braintree.Customer.update(self.braintree_customer_id, {
                "first_name": first_name,
                "last_name": last_name,
                'company': self.company_name,
                'email': email,
            })
            if result.is_success:
                return result
            else:
                return None

        return None

    def __unicode__(self):
        return self.account_name()


class User(AbstractBaseUser, PermissionsMixin):
    """
    A user that belongs to an Account & UserProfile.
    Users can have different roles and privileges within an Account.
    A User is required for login.
    Companions that do not have login privileges will now have UserProfiles but not Users.


    account: The user's associated account. It is possible to not have an Acccount for example, staff users may not
        require an Account to login to the admin.
    first_name: The user's first name. Have to denormalize because User is based on django useradmin
    last_name: The user's last name.  Have to denormalize because User is based on django useradmin
    email: The user's email used for login.

    is_staff: If this user is a staff user and can access the admin.
    is_active: If this user account is active and can login.
    date_joined: The date this user joined.
    avatar: The original uploaded avatar image
    avatar_thumbnail: the processed avatar thumbnail for use on the site

    AbstractBaseUser
    ----------------
    password: The user's hashed password.
    last_login: The last time the user logged in.

    PermissionsMixin
    ----------------
    is_superuser: Designates that this user has all permissions without explicitly assigning them.
    groups: The groups this user belongs to. A user will get all permissions granted to each of their groups.
    user_permissions: Specific permissions for this user.
    """

    account = models.ForeignKey('accounts.Account', on_delete=models.SET_NULL, null=True, blank=True)
    userprofile = models.OneToOneField('accounts.UserProfile', related_name='user', null=True, blank=True)
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    email = models.EmailField(unique=True)

    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField(default=timezone.now)
    avatar = models.ImageField(upload_to='avatars', blank=True, null=True)
    avatar_thumbnail = ImageSpecField(source='avatar', processors=[Transpose(), ResizeToFill(200, 200)], format='JPEG', options={'quality': 80, 'optimize': True})

    objects = UserManager()

    USERNAME_FIELD = 'email'
    # REQUIRED_FIELDS = ['first_name', 'last_name'] -- these now exist on UserProfile
    # so email is really the only req. field now
    REQUIRED_FIELDS = []

    class Meta:
        permissions = (
            ('can_manage_companions', 'Can manage companions'),
            ('can_manage_team', 'Can manage team members for corporations'),
            ('can_manage_plan', 'Can manage account plan'),
            ('can_manage_billing', 'Can manage account billing information'),
            ('can_mange_invites', 'Can manage account invites'),
            ('can_fly', 'User can fly on flights'),
            ('can_book_flights', 'User can book their own flights'),
            ('can_book_team', 'User can book on behalf of other account users'),
            ('can_book_promo_flights', 'User can book their own promo flights'),
            ('can_buy_companion_passes', 'User can purchase companion passes'),
            ('can_buy_passes', 'User can purchase additional save my seat passes'),

            ('can_view_flights', 'Admin user can view flights'),
            ('can_update_flights', 'Admin user can update flight details'),
            ('can_edit_flights', 'Admin user can create or edit flights'),
            ('can_edit_flights_limited', 'Admin user can create or edit limited flight data'),
            ('can_view_members', 'Admin user can view member profile details'),
            ('can_edit_members', 'Admin user can edit member profile details'),
            ('can_book_members', 'Admin user can book flights on behalf of members'),
            ('can_charge_members', 'Admin user can make charges to a member\'s account'),
            ('can_background_check', 'Admin user can do background checks'),

            ('can_edit_account_status', 'Rise Admin user can edit account status'),
            ('can_merge_accounts', 'Rise Admin user can merge accounts'),
            ('can_reset_user_password', "Rise Admin user can reset a user's password."),
            ('can_edit_user_role', "Rise Admin user can edit a user's role."),
            ('can_edit_account_price', 'Rise Admin user can edit account price.'),

            ('can_manage_staff', 'Super Admin user can manage staff'),

            ('can_view_reports', 'Admin can view reports'),

            ('can_manage_announcements', 'Rise Admin user can manage announcements')

        )

    @property
    def user_profile(self):
        """
        Exists for backwards compatibility
        Returns:

        """
        return self.userprofile

    def can_fly(self):
        """
        Returns true if this user can fly
        """
        return self.has_perm('accounts.can_fly')

    def delete(self):
        """
        'Deletes' a user

        Currently just sets the user inactive
        """
        self.is_active = False
        self.save()

    def get_full_name(self):
        """
        Returns the user's full name
        """
        return '%s %s' % (self.first_name, self.last_name)

    def get_short_name(self):
        """
        Returns the user's first name for their short name
        """
        return self.first_name

    def avatar_url(self):
        """
        if the user has uploaded an avatar, use that, otherwise fall back
        to using gravatar

        returns an URL for use as the avatar URL
        """
        if self.avatar:
            return self.avatar_thumbnail.url

        default_avatar = settings.DEFAULT_AVATAR
        default_avatar = urllib.quote_plus(default_avatar)
        gravatar_url = 'https://www.gravatar.com/avatar/%s?s=200&d=%s' % (hashlib.md5(self.email.lower()).hexdigest(), default_avatar)
        return gravatar_url

    def is_coordinator(self):
        return self.groups.filter(name='Coordinator').exists()

    def is_companion(self):
        return self.groups.filter(name='Companion').exists()

    def is_admin(self):
        return self.groups.filter(name='Admin').exists()

    def __unicode__(self):
        return self.email

    def send_welcome_email(self):
        """
        Sends this user a welcome email which allows them to set their password and then begin setting up their profile
        """
        context = {
            'user': self,
            'uid': urlsafe_base64_encode(force_bytes(self.pk)),
            'token': invite_token_generator.make_token(self),
        }

        subject = 'Set up your Rise profile!'

        #RISE 498 - depending on which "welcome" they pick, they might send a "welcome" when they need to send onboarding.
        #the primary member should always get an onboarding email because that one has the contract.

        if self.account.primary_user == self:
            send_html_email('emails/founder_onboarding', context, subject, settings.DEFAULT_FROM_EMAIL, [self.email])
        elif self.is_coordinator():
            send_html_email('emails/coordinator_welcome', context, subject, settings.DEFAULT_FROM_EMAIL, [self.email])
        elif self.account.is_corporate():
            send_html_email('emails/founder_welcome', context, subject, settings.DEFAULT_FROM_EMAIL, [self.email])
        else:
            send_html_email('emails/member_welcome', context, subject, settings.DEFAULT_FROM_EMAIL, [self.email])

    def send_onboarding_email(self):
        """
        Sends this user the onboarding email so that they can begin setting up their account information.
        """
        context = {
            'user': self,
            'uid': urlsafe_base64_encode(force_bytes(self.pk)),
            'token': invite_token_generator.make_token(self),
        }

        subject = 'Set up your Rise profile!'

        send_html_email('emails/founder_onboarding', context, subject, settings.DEFAULT_FROM_EMAIL, [self.email])

    def send_anywhere_onboarding_email(self, flightset, flight_creator):
        """
        Sends this user the onboarding email so that they can begin setting up their account information.
        """
        context = {
            'user': self,
            'uid': urlsafe_base64_encode(force_bytes(self.pk)),
            'token': invite_token_generator.make_token(self),
            'flightset': flightset,
            'flight_creator': flight_creator
        }

        subject = 'Set up your Rise Anywhere profile!'

        send_html_email('emails/anywhere_onboarding', context, subject, settings.DEFAULT_FROM_EMAIL, [self.email])

    def send_staff_welcome_email(self):
        """
        Sends this staff user a welcome email which allows them to set their password and then begin setting up their profile
        """
        context = {
            'user': self,
            'uid': urlsafe_base64_encode(force_bytes(self.pk)),
            'token': invite_token_generator.make_token(self),
        }

        subject = 'Set up your Rise profile!'

        send_html_email('emails/staff_welcome', context, subject, settings.DEFAULT_FROM_EMAIL, [self.email], attachments=[])

    def generate_register_login_url(self):
        """
        Generates a unique URL for this user to login with to begin the register flow
        """
        signer = Signer()
        value = signer.sign(self.id)
        pk, signature = value.split(':')

        return reverse('register_login', kwargs={'pk': pk, 'signature': signature})


class UserProfile(models.Model):
    """
    The primary "person" record.
    We have moved the essential fields not relating to login & permissions to this record.

    # user: The user this profile is associated with -- removed because the FK now exists on User.
    # and not all UserProfiles have a User.
    first_name
    last_name
    email (optional & not necessarily unique for this record, mandatory for User record since it is login key.)
    origin_airport: The airport which this person will primarily fly out of
    background_status: The status of the person's background check. Choices are not started, processing, and either passed
        or failed depending on the outcome of the background check.
    phone: The person's phone number
    mobile_phone: The person's mobile/cell phone number
    billing_address: The person's billing address
    shipping_address: The person's shipping address

    food_options: The person's food preferences for meals served (if any)
    allergies: The person's food allergies (if any)

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

    WEIGHT_RANGE_CHOICES = (
        (99, '< 100'),
        (100, '100 - 124'),
        (125, '125 - 149'),
        (150, '150 - 174'),
        (175, '175 - 199'),
        (200, '200 - 224'),
        (225, '225 - 249'),
        (250, '250 - 274'),
        (275, '275 - 299'),
        (300, '300 - 324'),
        (325, '325 - 349'),
        (350, '350+'),
    )
    account = models.ForeignKey('accounts.Account', on_delete=models.SET_NULL, null=True, blank=True, related_name='userprofile_account')

    # user = models.OneToOneField('accounts.User', related_name='user_profile')
    first_name = models.CharField(max_length=30, null=False, blank=False)
    last_name = models.CharField(max_length=30, null=False, blank=False)
    email = models.EmailField(unique=False,null=True,blank=True)

    origin_airport = models.ForeignKey('flights.Airport', on_delete=models.SET_NULL, null=True, blank=True)
    title = models.CharField(max_length=128, blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    background_status = models.PositiveIntegerField(choices=BACKGROUND_CHOICES, default=BACKGROUND_NOT_STARTED)
    weight = models.PositiveIntegerField(choices=WEIGHT_RANGE_CHOICES, default=0)
    phone = PhoneNumberField(blank=True, null=True)
    mobile_phone = PhoneNumberField(blank=True, null=True)
    billing_address = models.ForeignKey('accounts.Address', on_delete=models.SET_NULL, null=True, blank=True, related_name='userprofile_billing_address_set')
    shipping_address = models.ForeignKey('accounts.Address', on_delete=models.SET_NULL, null=True, blank=True, related_name='userprofile_shipping_address_set')

    food_options = models.ManyToManyField('accounts.FoodOption', blank=True)
    allergies = models.CharField(max_length=1024, blank=True, null=True)

    alert_flight_email = models.BooleanField(default=True)
    alert_flight_sms = models.BooleanField(default=False)
    alert_promo_email = models.BooleanField(default=True)
    alert_promo_sms = models.BooleanField(default=False)
    alert_billing_email = models.BooleanField(default=True)
    alert_billing_sms = models.BooleanField(default=False)

    def __unicode__(self):
        return '%s' % (self.get_full_name())

    def get_full_name(self):
        """
        Returns the user's full name
        """
        return '%s %s' % (self.first_name, self.last_name)

    def avatar(self):
        if self.user:
            return self.user.avatar
        return None

    def avatar_url(self):
        if self.user:
            return self.user.avatar_url()
        default_avatar = settings.DEFAULT_AVATAR
        default_avatar = urllib.quote_plus(default_avatar)
        gravatar_url = 'https://www.gravatar.com/avatar/%s?s=200&d=%s' % (hashlib.md5(self.email.lower()).hexdigest(), default_avatar)
        return gravatar_url

    def active_noshow_restriction(self):
        now = datetime.datetime.now(pytz.utc)
        return UserNoShowRestrictionWindow.objects.filter(userprofile=self, start_date__lte=now, end_date__gte=now).first()


class FoodOption(models.Model):
    """
    title: The title for the food option
    description: An extended description of the food option (if any)
    """

    title = models.CharField(max_length=128)
    description = models.CharField(max_length=1024, blank=True, null=True)

    def __unicode__(self):
        return '%s' % (self.title)


class Invite(models.Model):
    """
    An invite to Rise

    account: The account that owns the invite or None if created by the system
    code: The invite code to use on signup
    invite_type: The type of invite. Either a physical card or a digital emailed code
    created_on: When this invite was created.
    created_by: The user that created this invite or None if created by the system
    redeemed: Whether or not this invite has been redeemed.
    redeemed_on: If redeemed, when it was redeemed.
    redeemed_by: The user that redeemed this invite code.
    origin_city: The origin city as indicated by the user when they signed up for the waitlist

    email: If a digital invite code, the email it was sent to.
    """

    VALID_CODES = ('TRAVELBETTER', 'TRAVEL BETTER', 'FLYBETTER', 'FLY BETTER', 'FLY RISE', 'FLYRISE', 'NEW FRIENDS',
                   'NEWFRIENDS','ANYWHERE')
    #  ANYWHERE is for AnywhereBasic.  We will add additional codes when we have additional service levels for Anywhere.

    INVITE_TYPE_PHYSICAL = 0
    INVITE_TYPE_DIGITAL = 1

    INVITE_TYPE_CHOICES = (
        (INVITE_TYPE_PHYSICAL, 'Physical Invite Card Code'),
        (INVITE_TYPE_DIGITAL, 'Emailed Invite Code'),
    )

    account = models.ForeignKey('accounts.Account', on_delete=models.SET_NULL, null=True, blank=True)
    code = models.CharField(max_length=32, db_index=True)
    invite_type = models.PositiveIntegerField(choices=INVITE_TYPE_CHOICES, default=INVITE_TYPE_DIGITAL)
    created_on = models.DateTimeField(default=timezone.now)
    created_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name="user_invitations")
    redeemed = models.BooleanField(default=False)
    redeemed_on = models.DateTimeField(blank=True, null=True)
    redeemed_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, related_name='redeemed_invite_set')
    origin_city = models.ForeignKey('accounts.City', on_delete=models.SET_NULL, null=True)

    first_name = models.CharField(max_length=30, blank=True, null=True)
    last_name = models.CharField(max_length=30, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    phone = PhoneNumberField(blank=True, null=True)

    objects = InviteManager()

    @classmethod
    def validate_code(cls, code):
        """
        Validates a given code is a generic valid code or unique invite code.

        Returns an invite object, or None if not a valid code
        """
        if code.upper() in Invite.VALID_CODES:
            # return a generic Invite object
            return Invite(code=code)

        # try and look up a valid, un-used code, else get None
        invite = next(iter(Invite.objects.filter(code=code, redeemed=False).select_related('origin_city')), None)

        return invite

    def is_physical(self):
        return self.invite_type == Invite.INVITE_TYPE_PHYSICAL

    def __unicode__(self):
        return self.code


class Address(models.Model):
    """
    A physical US address
    """

    street_1 = models.CharField(max_length=128)
    street_2 = models.CharField(max_length=128, blank=True, null=True)
    city = models.CharField(max_length=64)
    postal_code = models.CharField(max_length=10)
    state = USStateField()

    def __unicode__(self):
        if self.street_2:
            return '%s\n%s\n%s, %s %s' % (self.street_1, self.street_2, self.city, self.state, self.postal_code)
        return '%s\n%s, %s %s' % (self.street_1, self.city, self.state, self.postal_code)


class City(models.Model):
    """
    A city option for a user to choose during sign up for preferred cities

    name: The name of the city
    """

    MAX_FOUNDER_MEMBERS = 100
    MAX_OTHER_MEMBERS = 50

    name = models.CharField(max_length=50)
    is_launched = models.BooleanField(blank=True, default=False)
    is_accepting_members = models.BooleanField(blank=True, default=True)
    is_accepting_founders = models.BooleanField(blank=True, default=True)
    airport = models.ForeignKey('flights.Airport', on_delete=models.SET_NULL, null=True, blank=True, related_name='airport_city')

    def __unicode__(self):
        if not self.is_launched:
            return '%s*' % self.name
        return self.name

    @cached_property
    def founder_count(self):
        """
        Returns the number of founders for this city.
        """
        return self.members.filter(founder=True).count()

    @cached_property
    def member_count(self, refresh_cache=False):
        """
        Returns the number of total members including founders for this city.
        """
        return self.members.all().count()

    def is_founder(self):
        """
        If based on the current member count, if this is a founder level city still
        """
        return self.member_count < City.MAX_FOUNDER_MEMBERS

    def update_member_acceptance(self):
        """
        Checks current members and founding members and sets is_accepting_members and is_accepting founders appropriately
        """
        if self.member_count >= City.MAX_FOUNDER_MEMBERS:
            self.is_accepting_founders = False

        if self.member_count >= City.MAX_FOUNDER_MEMBERS + City.MAX_OTHER_MEMBERS:
            self.is_accpeting_members = False

        self.save()


class WaitList(models.Model):
    """
    A signup wait list

    first_name: User's first name
    last_name: User's last name
    email: User's email
    added: When the user was added to the waitlist
    invite: The invite sent to the user
    """

    email = models.EmailField()
    added = models.DateTimeField(default=timezone.now)
    invite = models.ForeignKey('accounts.Invite', on_delete=models.SET_NULL, null=True)

    def __unicode__(self):
        pass


class UserNoShow(models.Model):
    # tracks an individual time that a person no-showed
    # adding both userprofile and user in preparation for inversion of control
    userprofile = models.ForeignKey('accounts.UserProfile', related_name='userprofile_noshow')
    user = models.ForeignKey('accounts.User', related_name='user_noshow', null=True, blank=True)
    flight = models.ForeignKey('flights.Flight', on_delete=models.SET_NULL, null=True)
    created = models.DateTimeField(auto_now_add=True) # need this so even if flight is deleted we know when it was.


class UserNoShowRestrictionWindow(models.Model):
    # records a window of time that a person is not allowed to fly because of no-show behavior
    # adding both userprofile and user in preparation for inversion of control
    userprofile = models.ForeignKey('accounts.UserProfile', related_name='userprofile_noshowrestriction')
    user = models.ForeignKey('accounts.User', related_name='user_noshowrestriction', null=True, blank=True)
    start_date = models.DateTimeField(null=False)
    end_date = models.DateTimeField(null=False)


class UserNote(models.Model):
    """
    Notes for a user profile

    user: The user whom the note regards
    created_by: The user who added the note
    created: When the note was added
    body: The body of the note
    """

    user = models.ForeignKey('accounts.User', null=True, blank=True, related_name='note_user')
    userprofile = models.ForeignKey('accounts.UserProfile', null=True,blank=True, related_name='note_userprofile')
    created_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name="created_by")
    created = models.DateTimeField(auto_now_add=True)
    body = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ["-created"]

    def __unicode__(self):
        return 'Note for %s on %s' % (self.userprofile, self.created)


auditlog.register(Account, include_fields=['founder', 'vip', 'status', 'activated', 'plan', 'company_name',
    'primary_user', 'account_type', 'corporate_amount', 'payment_method', 'member_count', 'pass_count',
    'companion_pass_count', 'available_passes', 'available_companion_passes', 'complimentary_passes',
    'complimentary_companion_passes', 'onboarding_fee_paid'])


class OncallSchedule(models.Model):
    HOURS=(
        (0,'12:00 AM'),(1,'1:00 AM'),(2,'2:00 AM'),(3,'3:00 AM'),(4,'4:00 AM'),(5,'5:00 AM'),
        (6,'6:00 AM'),(7,'7:00 AM'),(8,'8:00 AM'),(9,'9:00 AM'),(10,'10:00 AM'),(11,'11:00 AM'),(12,'12:00 PM'),
        (13,'1:00 PM'),(14,'2:00 PM'),(15,'3:00 PM'),(16,'4:00 PM'),(17,'5:00 PM'),(18,'6:00 PM'),(19,'7:00 PM'),
        (20,'8:00 PM'),(21,'9:00 PM'),(22,'10:00 PM'),(23,'11:00 PM')
    )
    user = models.ForeignKey('accounts.User')
    start_date = models.DateTimeField('Start Date', null=True,blank=True)
    end_date = models.DateTimeField('End Date', null=True,blank=True)
    airport = models.ForeignKey('flights.Airport', null=True)
    flights = models.ManyToManyField('flights.Flight',null=True)

    def local_time_start_date(self):
        """
        Return the depature time localized to the origin timezone
        """
        return arrow.get(self.start_date).to(timezone.get_current_timezone()).datetime

    def local_time_end_date(self):
        """
        Return the depature time localized to the origin timezone
        """
        return arrow.get(self.end_date).to(timezone.get_current_timezone()).datetime

    def get_flights(self):
        return self.flights.all()


class BillingPaymentMethod(models.Model):

    PAYMENT_CREDIT_CARD = 'C'
    PAYMENT_ACH = 'A'

    PAYMENT_CHOICES = (
        (PAYMENT_CREDIT_CARD, 'Credit Card'),
        (PAYMENT_ACH, 'ACH'),
    )
    account = models.ForeignKey('accounts.Account')
    payment_method = models.CharField(max_length=1, default=PAYMENT_CREDIT_CARD, choices=PAYMENT_CHOICES)
    nickname = models.CharField(max_length=20,null=True)
    is_default = models.BooleanField(default=False)

    objects = PaymentMethodManager()

