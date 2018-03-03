# coding=utf-8
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.functional import cached_property

from datetime import date, timedelta
import arrow
from decimal import Decimal, ROUND_HALF_UP
import braintree
import stripe
import logging
from htmlmailer.mailer import send_html_email
import datetime
from .managers import CardManager, InvoiceLineItemManager, InvoiceManager, SubscriptionManager, ChargeManager
from .utils import convert_timestamp
from accounts.models import UserProfile, Account, BillingPaymentMethod
from dateutil.relativedelta import relativedelta


logger = logging.getLogger(__name__)
stripe.api_key = settings.STRIPE_API_KEY


class GenericBillingException(Exception):  pass


class InvalidUpgradeException(Exception):
    pass

class IncompleteUpgradeException(Exception):
    pass

class Card(models.Model):
    """
    A stripe credit card

    account: The account assocaited with this credit card
    token: the vault token for this credit card
    last4: the last 4 digits of the credit card
    brand: the brand of the credit card
    exp_month: the month the card expires
    exp_year: the year the credit card expires
    """

    account = models.ForeignKey('accounts.Account')
    token = models.CharField(max_length=64, db_index=True)
    last4 = models.CharField(max_length=4)
    brand = models.CharField(max_length=32)
    exp_month = models.PositiveIntegerField()
    exp_year = models.PositiveIntegerField()
    billing_payment_method = models.OneToOneField('accounts.BillingPaymentMethod',null=True)

    objects = CardManager()

    def is_default(self):
        pay_method = BillingPaymentMethod.objects.filter(id=self.billing_payment_method_id,is_default=True).first()
        if pay_method is not None:
            return True
        else:
            return False

    def charge(self, amount, description, created_by=None):
        """
        Charge this card the given amount for the given description

        Returns the Charge object or throws an exception
        """
        user = self.account.primary_user
        first_name = ''
        last_name = ''
        email = ''
        if user:
            first_name = user.first_name
            last_name = user.last_name
            email = user.email

        result = braintree.Transaction.sale({
            'customer_id': self.account.braintree_customer_id,
            'amount': amount,
            'options': {
                'submit_for_settlement': True,
            },
            "customer": {
                'first_name': first_name,
                'last_name': last_name,
                'company': self.account.company_name,
                'email': email
            },
        })

        if result.is_success:
            charge = Charge.objects.create_from_braintree_transaction(result.transaction, self.account, self, description, created_by)
            return charge
        else:
            raise GenericBillingException(result.message)

    def delete(self, *args, **kwargs):
        """
        Delete this credit card from braintree and locally
        """
        try:
            braintree.PaymentMethod.delete(self.token)
        except Exception as e:
            logger.exception('Unable to delete the card in braintree')
        return super(Card, self).delete(*args, **kwargs)

    def __unicode__(self):
        return '%s %s (%s/%s)' % (self.brand, self.last4, self.exp_month, self.exp_year,)


class BankAccount(models.Model):
    """
    A Stripe bank account

    account: The account associated with this bank account
    stripe_id: The stripe id for this bank account
    bank_name: The name of the bank
    last4: the last4 of the account number
    routing_number: the bank's routing number
    verified: if this account has been verified
    """

    account = models.ForeignKey('accounts.Account')
    stripe_id = models.CharField(max_length=64, db_index=True)
    bank_name = models.CharField(max_length=128)
    last4 = models.CharField(max_length=4)
    routing_number = models.CharField(max_length=32)
    verified = models.BooleanField(default=False)
    billing_payment_method = models.OneToOneField('accounts.BillingPaymentMethod',null=True)

    def __unicode__(self):
        return u'%s %s %s' % (self.bank_name, self.routing_number, self.last4)

    def is_default(self):
        pay_method = BillingPaymentMethod.objects.filter(id=self.billing_payment_method_id,is_default=True).first()
        if pay_method is not None:
            return True
        else:
            return False

    def charge(self, amount, description, created_by=None):
        """
        Charge this bank account the given amount for the given description by the given user
        """
        payment = stripe.Payment.create(amount=int(amount * 100), currency='USD', payment_method='ach', customer=self.account.stripe_customer_id, description=description, source=self.stripe_id)

        charge = Charge.objects.create_from_stripe_payment(payment, self.account, self, description, created_by)

        return charge

    def update_from_stripe_bank_account(self, stripe_bank_account):
        self.stripe_id = stripe_bank_account.id
        self.last4 = stripe_bank_account.last4
        self.bank_name = stripe_bank_account.bank_name
        self.routing_number = stripe_bank_account.routing_number
        self.verified = stripe_bank_account.verified

    def delete(self, *args, **kwargs):
        """
        Delete this bank account from Stripe and locally
        """
        stripe_customer = self.account.get_stripe_customer()
        stripe_customer.bank_accounts.retrieve(self.stripe_id).delete()
        return super(BankAccount, self).delete(*args, **kwargs)

    def send_welcome_email(self):
        subject = 'Welcome to Rise'

        user = self.account.primary_user

        context = {
            'user': user,
            'user_profile': next(iter(UserProfile.objects.filter(user=user).select_related()), None),
        }

        send_html_email('emails/welcome_ach', context, subject, settings.DEFAULT_FROM_EMAIL, [user.email])


class Charge(models.Model):
    """
    A charge for an account. This can either be a Stripe charge or a manual charge added to an account.

    account: The account associated with this charge
    subscription: The subscription associated with this charge if one
    payment_method: How
    vault_id: The ID of this charge, if assocaited with Stripe or Braintree
    amount: The amount of this charge.
    amount_refunded: The amount refunded for this charge, if any.
    description: The description of this charge if any.
    status: The braintree status of this charge
    captured: If the charge was created without capturing, this boolean represents whether or not it is still uncaptured
        or has since been captured.
    paid: If this charge has been paid.
    disputed: if this charge is being disputed.
    refudned: Whether or not the charge has been fully refunded. If the charge is only partially refunded, this
        attribute will still be false.
    failure_code: Error code explaining reason for charge failure if available (see https://stripe.com/docs/api#errors
        for a list of codes).
    failure_message: Message to user further explaining reason for charge failure if available.
    created: When this charge was created
    created_by: Who created this charge, if None, this was created by the system via Stripe webhook
    """

    PAYMENT_METHOD_MANUAL = 'M'
    PAYMENT_METHOD_BANK = 'B'
    PAYMENT_METHOD_CARD = 'C'

    PAYMENT_METHOD_CHOICES = (
        (PAYMENT_METHOD_MANUAL, 'Manual'),
        (PAYMENT_METHOD_BANK, 'Bank Account'),
        (PAYMENT_METHOD_CARD, 'Card'),
    )

    account = models.ForeignKey('accounts.Account', blank=True, null=True)
    subscription = models.ForeignKey('billing.Subscription', on_delete=models.SET_NULL, null=True, blank=True)
    payment_method = models.CharField(max_length=1, choices=PAYMENT_METHOD_CHOICES, default=PAYMENT_METHOD_MANUAL)
    card = models.ForeignKey('billing.Card', on_delete=models.SET_NULL, null=True, blank=True)
    bank_account = models.ForeignKey('billing.BankAccount', on_delete=models.SET_NULL, null=True, blank=True)
    vault_id = models.CharField(max_length=64, blank=True, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    amount_refunded = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    description = models.CharField(blank=True, null=True, max_length=256)
    status = models.CharField(max_length=64, blank=True, null=True)
    captured = models.BooleanField(default=False)
    paid = models.BooleanField(default=False)
    disputed = models.BooleanField(default=False)
    refunded = models.BooleanField(default=False)
    failure_code = models.CharField(max_length=64, blank=True, null=True)
    failure_message = models.TextField(blank=True, null=True)
    created = models.DateTimeField()
    created_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True)

    objects = ChargeManager()

    def update_from_stripe_charge(self, stripe_charge):
        """
        Updates this Charge fields from the given stripe charge object
        """

        self.vault_id = stripe_charge.id
        self.account = Account.objects.filter(stripe_customer_id=stripe_charge.customer).first()
        self.status = stripe_charge.status
        if stripe_charge.card:
            self.card = Card.objects.filter(token=stripe_charge.card.id).first()
        self.amount = stripe_charge.amount / Decimal('100')
        self.amount_refunded = stripe_charge.amount_refunded / Decimal('100')
        self.description = stripe_charge.description
        self.captured = stripe_charge.captured
        self.paid = stripe_charge.paid
        self.disputed = (stripe_charge.dispute is not None)
        self.refunded = stripe_charge.refunded
        self.failure_code = stripe_charge.failure_code
        self.failure_message = stripe_charge.failure_message
        self.created = convert_timestamp(stripe_charge.created)

    def is_stripe(self):
        """
        Returns True if this is a Stripe charge
        """
        return self.vault_id and self.vault_id.startswith('ch_')

    def is_credit_card(self):
        return self.payment_method == Charge.PAYMENT_METHOD_CARD

    def is_bank_account(self):
        return self.payment_method == Charge.PAYMENT_METHOD_BANK

    def is_manual(self):
        return self.payment_method == Charge.PAYMENT_METHOD_MANUAL

    def has_failed(self):
        """
        If this charge has failed
        """
        return self.status in ('failed',)

    def void(self, description, user):
        """
        Voids a braintree transaction
        """
        if self.is_voidable():
            result = braintree.Transaction.void(self.vault_id)
            if result.is_success:
                charge_refund = ChargeRefund.objects.create(charge=self, amount=self.amount, description=description, created=timezone.now(), created_by=user, vault_id=result.transaction.id)
                #need to record this got refunded
                self.refunded=True
                self.amount_refunded = self.amount
                self.save()
                return charge_refund
            else:
                raise GenericBillingException(result.message)

    def refund(self, amount, description, user):
        """
        Refunds the amount given with the given description and who refunded it
        """
        if amount <= 0:
            return

        # ensure this charge is refundable and there is enough left to refund the requested amount
        if self.is_refundable() and self.refund_amount_remaining() >= amount:
            if self.is_bank_account():
                payment = stripe.Payment.retrieve(self.vault_id)
                # Rise-152 add description to this refund transaction with stripe
                payment_refund = payment.refunds.create(amount=int(amount * 100), metadata={'description': description})

                charge_refund = ChargeRefund.objects.create(charge=self, amount=amount, description=description, created=timezone.now(), created_by=user, vault_id=payment_refund.id)

                amount_refunded = self.amount_refunded or 0
                self.amount_refunded = amount_refunded + amount
                self.refunded = True
                self.save()
            elif self.is_credit_card():
                if self.is_stripe():
                    stripe_charge = stripe.Charge.retrieve(self.vault_id)
                    stripe_refund = stripe_charge.refunds.create(amount=int(amount * 100), metadata={'description': description, 'refunded_by': user.get_full_name() if user else ''})

                    charge_refund = ChargeRefund.objects.create(charge=self, amount=amount, description=description, created=timezone.now(), created_by=user, vault_id=stripe_refund.id)

                    stripe_charge = stripe.Charge.retrieve(self.vault_id)
                    self.update_from_stripe_charge(stripe_charge)
                    self.refunded = True
                    self.save()

                    return charge_refund
                else:  # braintree
                    braintree_transaction = braintree.Transaction.find(self.vault_id)
                    result = braintree.Transaction.refund(braintree_transaction.id, amount)

                    if result.is_success:
                        charge_refund = ChargeRefund.objects.create(charge=self, amount=amount, description=description, created=timezone.now(), created_by=user, vault_id=result.transaction.id)

                        amount_refunded = self.amount_refunded or 0
                        self.amount_refunded = amount_refunded + amount
                        self.refunded = True
                        self.save()

                        return charge_refund
                    else:
                        raise GenericBillingException(result.message)

            elif self.is_manual():
                amount_refunded = self.amount_refunded or 0
                self.amount_refunded = amount_refunded + amount
                self.refunded = True
                self.save()
                charge_refund = ChargeRefund.objects.create(charge=self, amount=amount, description=description, created=timezone.now(), created_by=user)
                return charge_refund
        else:
            raise GenericBillingException("Status invalid for refund or insufficient funds to refund.")

    def is_voidable(self):
        """
        Returns if this braintree transaction can be voided
        In addition to status also check and make sure there wasn't already partial refund on it.
        """
        if self.amount_refunded > 0 or self.refunded:
            return False

        if self.is_credit_card() and not self.is_stripe():
            braintree_transaction = braintree.Transaction.find(self.vault_id)
            if braintree_transaction.status in ('authorized', 'submitted_for_settlement',):
                return True

        return False


    def get_transaction(self):
        """
        Required by the Transaction Test Harness functionality for manually modifying status
        In the test environments ONLY.
        Returns:

        """
        if self.is_credit_card():
            if not self.is_stripe():
                return braintree.Transaction.find(self.vault_id)
        return None

    def is_refundable(self):
        """
        Returns true if this charge is refundable still
        """
        if self.amount_refunded is not None and self.amount <= self.amount_refunded:
            return False

        if self.is_credit_card():
            if self.is_stripe():
                return self.captured
            else:
                braintree_transaction = braintree.Transaction.find(self.vault_id)
                if braintree_transaction.status not in ('settled', 'settling',):
                    return False

        return True

    def refund_amount_remaining(self):
        """
        Returns the refund amount remaining
        """
        if self.amount_refunded is None:
            return self.amount

        return self.amount - self.amount_refunded

    def send_receipt_email(self, subtotal=None, tax=None, tax_percentage=None):
        """
        Send a receipt email for this charge

        If this charge has an invoice, send the receipt email from the invoice instead
        """

        subject = 'Receipt for Your Payment to Rise, LLC.'

        user = self.account.primary_user

        context = {
            'charge': self,
            'user': user,
            'user_profile': next(iter(UserProfile.objects.filter(user=user).select_related()), None),
            'subtotal': subtotal,
            'tax': tax,
            'tax_percentage': tax_percentage
        }

        send_html_email('emails/payment_receipt', context, subject, settings.DEFAULT_FROM_EMAIL, [user.email])

    def send_welcome_receipt_email(self):
        """
        Send a receipt email for this charge

        If this charge has an invoice, send the receipt email from the invoice instead
        """

        subject = 'Receipt for Your Payment to Rise, LLC.'

        user = self.account.primary_user

        context = {
            'charge': self,
            'user': user,
            'user_profile': next(iter(UserProfile.objects.filter(user=user).select_related()), None),
        }

        send_html_email('emails/welcome_receipt', context, subject, settings.DEFAULT_FROM_EMAIL, [user.email])


    def send_rise_notification_email(self):
        """
        Sends a notification of failed payment to Rise
        """
        subject = 'Payment Failed'

        context = {
            'error_message': self.failure_message,
            'account': self.account,
        }

        send_html_email('emails/admin_payment_failed_notification', context, subject, settings.DEFAULT_FROM_EMAIL, ['support@iflyrise.com'])

    def __unicode__(self):
        return 'Amount %s' % (self.amount,)


class ChargeRefund(models.Model):
    """
    A model to track refunds issued for charges

    charge: the charge this refund is related to
    amount: the amount refunded
    description: Optional description of the refund
    created: when the refund was issues
    created_by: who issued the refund
    """

    charge = models.ForeignKey('billing.Charge')
    vault_id = models.CharField(max_length=64, blank=True, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.CharField(blank=True, null=True, max_length=256)
    created = models.DateTimeField()
    created_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True)

    def __unicode__(self):
        return 'Refund %s' % (self.amount)


class Plan(models.Model):
    """
    A subscription plan. Plan details (price, interval, etc.) are, by design, not editable.

    name: Name of this membership tier
    description: A description of the plan
    anywhere_only:  True if this is a RiseAnywhere only membership level
    amount: The re-occurring fee for this membership level
    pass_count: The number of "Save my Seat" passes.
    companion_passes: The number of complimentary companion passes per
    active: If true, users can sign-up or change membership to this tier. If false, allows existing users
        to continue using this membership tier until either forced or choose to upgrade to an active tier.
    interval: One of day, week, month or year. The frequency with which a subscription should be billed.
    interval_count: The number of intervals (specified in the interval property) between each subscription billing.
        For example, interval=month and interval_count=3 bills every 3 months.
    """

    INTERVAL_DAY = 'day'
    INTERVAL_WEEK = 'week'
    INTERVAL_MONTH = 'month'
    INTERVAL_YEAR = 'year'

    INTERVAL_CHOICES = (
        (INTERVAL_DAY, 'Daily'),
        (INTERVAL_WEEK, 'Weekly'),
        (INTERVAL_MONTH, 'Monthly'),
        (INTERVAL_YEAR, 'Yearly'),
    )

    name = models.CharField(max_length=64)
    description = models.TextField(blank=True, null=True)
    anywhere_only = models.BooleanField(default=False, null=False)
    has_onboarding = models.BooleanField(default=True, null=False)
    # change to property where we can look at plan contract
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    interval = models.CharField(choices=INTERVAL_CHOICES, max_length=16, default=INTERVAL_MONTH)
    interval_count = models.PositiveIntegerField(default=1)
    pass_count = models.PositiveIntegerField(default=2)
    companion_passes = models.PositiveIntegerField(default=0)
    active = models.BooleanField(default=True)
    requires_contract = models.BooleanField(default=False)

    def get_stripe_metadata(self):
        """
        Returns a dictionary of meta data for the stripe plan
        """
        return {
            'pass_count': self.pass_count,
            'companion_passes': self.companion_passes,
            'active': self.active,
        }

    def create_stripe_plan(self):
        """
        Creates this plan in Stripe
        """
        stripe_plan = stripe.Plan.create(id=str(self.id), name=self.name, interval=self.interval, interval_count=self.interval_count, amount=int(self.amount * 100), currency='usd', metadata=self.get_stripe_metadata(), statement_description=self.name[:15])
        return stripe_plan

    def __unicode__(self):
        return self.name

class PlanContractPrice(models.Model):
    """
    Allows for differential pricing based on length of contract.
    """
    CONTRACT_3MONTH = 3
    CONTRACT_6MONTH = 6
    CONTRACT_12MONTH = 12

    CONTRACT_LENGTH_CHOICES = (
        (CONTRACT_3MONTH, '3 Month'),
        (CONTRACT_6MONTH, '6 Month'),
        (CONTRACT_12MONTH, '12 Month')
    )
    contract_length = models.PositiveIntegerField(choices=CONTRACT_LENGTH_CHOICES)
    plan = models.ForeignKey('billing.Plan', on_delete=models.SET_NULL, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    selectable = models.BooleanField(null=False, blank=False, default=True)

    def __str__(self):
        return self.plan.name + ": " + str(self.contract_length) + " month - $" + str(self.amount)

    @property
    def description_without_price(self):
        return self.plan.name + ": " + str(self.contract_length) + " month contract"



class Subscription(models.Model):
    """
    An account's subscription allowing recurring charges

    account: The account for whom this subscription is charging
    description: A description for this subscription
    amount: how much this subscription is for which does not include tax
    tax_percentage: The tax percentage to charge for this subscription, defaults to 7.5%

    status: Possible values are trialing, active, past_due, canceled, or unpaid. A subscription still in its trial period
        is trialing and moves to active when the trial period is over. When payment to renew the subscription fails, the
        subscription becomes past_due. After Stripe has exhausted all payment retry attempts, the subscription ends up
        with a status of either canceled or unpaid depending on your retry settings. Note that when a subscription has a
        status of unpaid, no subsequent invoices will be attempted (invoices will be created, but then immediately
        automatically closed. Additionally, updating customer card details will not lead to Stripe retrying the latest
        invoice.). After receiving updated card details from a customer, you may choose to reopen and pay their closed invoices.
    billing_day_of_month: The day of month for which this subscription should bill
    period_end: End of the current period that the subscription has been invoiced for. At the end of this
        period, a new invoice will be created.
    period_start: Start of the current period that the subscription has been invoiced for
    canceled_at: If the subscription has been canceled, the date of that cancellation. If the subscription was canceled
        with cancel_at_period_end, canceled_at will still reflect the date of the initial cancellation request, not the
        end of the subscription period when the subscription is automatically moved to a canceled state.
    """

    SUBSCRIPTION_STATUS_ACTIVE = 'active'
    SUBSCRIPTION_STATUS_PAST_DUE = 'past_due'
    SUBSCRIPTION_STATUS_CANCELLED = 'canceled'
    SUBSCRIPTION_STATUS_PENDING_PAYMENT = 'pending'

    SUBSCRIPTION_STATUS_CHOICES = (
        (SUBSCRIPTION_STATUS_ACTIVE, 'Active'),
        (SUBSCRIPTION_STATUS_PAST_DUE, 'Past Due'),
        (SUBSCRIPTION_STATUS_CANCELLED, 'Cancelled'),
        (SUBSCRIPTION_STATUS_PENDING_PAYMENT, 'Pending Payment'),
    )

    account = models.ForeignKey('accounts.Account', blank=True, null=True)
    description = models.CharField(max_length=256, blank=True, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    tax_percentage = models.DecimalField(max_digits=10, decimal_places=10, default=settings.FET_TAX)
    status = models.CharField(max_length=16, choices=SUBSCRIPTION_STATUS_CHOICES, default=SUBSCRIPTION_STATUS_ACTIVE)
    billing_day_of_month = models.PositiveIntegerField(default=1)
    period_start = models.DateField(blank=True, null=True)
    period_end = models.DateField(blank=True, null=True)
    canceled_at = models.DateTimeField(blank=True, null=True)
    created = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True)

    objects = SubscriptionManager()

    @cached_property
    def tax(self):
        """
        Returns the tax amount for this subscription
        """
        return (self.amount * self.tax_percentage).quantize(Decimal('0.00'), rounding=ROUND_HALF_UP)

    def total(self):
        """
        Returns the total amount to be billed for this subscription including tax
        """
        return self.amount + self.tax

    def bill(self,payment_method_id=None,created_by=None):
        """
        Handling billing for this subscription
        """

        account = self.account
        today = date.today()
        # advance to the next billing period if active
        if not self.is_current_period():
            if account.do_not_renew == 0 and account.contract is not None \
                 and account.contract_end_date is not None and account.contract_end_date.date() < today and not account.is_corporate():
                account.contract_start_date = datetime.datetime.now()
                account.contract_end_date = account.contract_start_date + relativedelta(months=account.contract.contract_length)
                self.amount = account.contract.amount
                account.save()
            elif account.do_not_renew == 1 and account.contract is not None \
                    and account.contract_end_date is not None and account.contract_end_date.date() < today:
                account.status = Account.STATUS_CANCELLED
                self.status = Subscription.SUBSCRIPTION_STATUS_CANCELLED
                account.save()
                self.save()
                return
            self.advance_period()

        #only charge if the amount > 0
        if self.amount > 0:
            # try and charge the account
            try:
                # charge and update the charge for this subscription
                charge = self.charge(payment_method_id=payment_method_id,created_by=created_by)
                charge.subscription = self
                charge.save()

                # make sure the status is active
                if charge.is_bank_account():
                    self.status = Subscription.SUBSCRIPTION_STATUS_PENDING_PAYMENT
                else:
                    self.status = Subscription.SUBSCRIPTION_STATUS_ACTIVE
                self.save()

                if not self.account.is_manual() and not self.account.is_trial():
                    self.send_receipt_email(charge)

            except Exception, e:
                # update the subscription status as past due
                self.status = Subscription.SUBSCRIPTION_STATUS_PAST_DUE
                self.save()

                self.send_payment_failed_email(payment_method_id=payment_method_id)
                self.send_rise_notification_email(e.message)

    def is_current_period(self):
        """
        Returns True if today is in this subscriptions period
        """
        today = date.today()
        return self.period_start <= today <= self.period_end

    def get_next_date(self, start_date):
        """
        Returns a date 1 month from the given start
        """
        # increment the start by 1 month
        start = arrow.get(start_date).replace(months=1)
        # if the start day is not the correct billing day, try and move to billing day
        if start.day != self.billing_day_of_month:
            try:
                start = start.replace(day=self.billing_day_of_month)
            except ValueError:
                # day is out of range for month
                pass

        return start.date()

    def advance_period(self):
        """
        Advances the billing period

        Example for billing day is 31st:
        2015-02-28 2015-03-30
        2015-03-31 2015-04-29
        2015-04-30 2015-05-30
        2015-05-31 2015-06-29
        2015-06-30 2015-07-30
        2015-07-31 2015-08-30
        2015-08-31 2015-09-29
        2015-09-30 2015-10-30
        2015-10-31 2015-11-29
        2015-11-30 2015-12-30
        2015-12-31 2016-01-30
        2016-01-31 2016-02-28
        2016-02-29 2016-03-30
        2016-03-31 2016-04-29
        """
        self.period_start = self.get_next_date(self.period_start)
        self.period_end = arrow.get(self.get_next_date(self.period_start)).replace(days=-1).date()
        self.save()

    def next_bill_date(self):
        """
        Returns the next billing date
        """
        if self.period_end is not None:
            return self.period_end + timedelta(days=1)
        else:
            return None

    def charge(self,payment_method_id=None,created_by=None):
        """
        Charge the acccount for this subscription
        """
        if payment_method_id is None:
            return self.account.charge(self.total(), self.description, created_by)
        else:
            pay_method = BillingPaymentMethod.objects.filter(pk=payment_method_id).first()
            if pay_method is not None and pay_method.payment_method == BillingPaymentMethod.PAYMENT_CREDIT_CARD:
                card = Card.objects.filter(billing_payment_method_id=payment_method_id).first()
                return card.charge(self.total(), self.description, created_by)
            elif pay_method is not None and pay_method.payment_method == BillingPaymentMethod.PAYMENT_ACH:
                bankaccount = BankAccount.objects.filter(billing_payment_method_id=payment_method_id).first()
                return bankaccount.charge(self.total(), self.description, created_by)


    def is_active(self):
        """
        Determins if this subscription is active
        """
        return self.status in (Subscription.SUBSCRIPTION_STATUS_ACTIVE, Subscription.SUBSCRIPTION_STATUS_PENDING_PAYMENT)

    def update_amount(self, amount, prorate=True, user=None):
        """
        Updates the amount of this subscription

        if prorate is true, it will prorate the subscription amount
        """
        # check to see if the amount is actually changing
        if self.amount == amount:
            return None
        elif self.period_start is None:
            logger.exception('period_start for subscription is None.')
            return None
        elif self.period_end is None:
            logger.exception('period_start for subscription is None.')
            return None

        #AMF  don't prorate if the previous subscription has already ended
        if prorate and (date.today() - self.period_end).days < 0:

            period_days = (self.period_end - self.period_start).days
            previous_period_days = (date.today() - self.period_start).days
            new_period_days = (self.period_end - self.period_start).days - previous_period_days

            previous_percentage = float(previous_period_days) / float(period_days)
            new_percentage = float(new_period_days) / float(period_days)

            previous_amount = self.total() * Decimal(previous_percentage)

            new_total = (amount * self.tax_percentage).quantize(Decimal('.00'), rounding=ROUND_HALF_UP) + amount

            new_amount = new_total * Decimal(new_percentage)

            total = (previous_amount + new_amount).quantize(Decimal('.00'), rounding=ROUND_HALF_UP)

            difference = total - self.total()

            description = 'Subscription proration from $%s to $%s' % (self.amount, amount)

            # AMF - Per Teresa, they want to handle refunds on a case by case basis.
            # This logic was broken before (the refund()  method aborts if you pass it a negative difference,
            # so you need to pass the absolute value of the difference if it is negative.
            # OLD COMMENT:  if the difference is less than 0, refund amount
            # If difference is positive, they owe money and we need to charge.

            if difference > 0:
                #AMF  put tracer in for a glitch - never charge if the old amount is higher than new:
                if self.amount > amount:
                    logger.error("Subscription change proration was about to be charged improperly:  original=%s, new=%s, difference=%s, current period end=%s" % (self.amount, amount, difference, self.period_end.strftime("M d, Y")))
                else:
                    charge = self.account.charge(difference, description, user)
                    charge.subscription=self
                    charge.save()
                    charge.send_receipt_email()

        self.amount = amount
        self.save()

    def cancel(self, refund=False, user=None):
        """
        Cancel's this subscription.

        refund: if True, will refund the remaining amount on the subscription
        """
        if refund:
            today = date.today()
            used_days = (today - self.period_start).days
            period_days = (self.period_end - self.period_start).days

            percent_remaining = float(period_days - used_days) / float(period_days)
            refund_amount = (Decimal(percent_remaining) * self.total()).quantize(Decimal('.00'), rounding=ROUND_HALF_UP)

            if refund_amount > 0:
                last_charge = self.get_last_charge()
                if last_charge is not None:
                    last_charge.refund(refund_amount, 'Subscription cancelled', user)

        self.canceled_at = timezone.now()
        self.status = Subscription.SUBSCRIPTION_STATUS_CANCELLED
        self.save()

    def get_last_charge(self):
        """
        Returns the last charge for this subscription
        """
        charge = next(iter(Charge.objects.filter(subscription=self).order_by('-created')[:1]), None)
        return charge

    def send_receipt_email(self, charge):
        """
        Send a receipt email for this charge

        If this charge has an invoice, send the receipt email from the invoice instead
        """

        subject = 'Receipt for Your Payment to Rise, LLC.'

        user = self.account.primary_user

        context = {
            'charge': charge,
            'subscription': self,
            'user': user,
            'user_profile': next(iter(UserProfile.objects.filter(user=user).select_related()), None),
        }

        send_html_email('emails/subscription_receipt', context, subject, settings.DEFAULT_FROM_EMAIL, [user.email])

    def send_payment_failed_email(self,payment_method_id=None):
        subject = 'Rise Payment Failed'

        user = self.account.primary_user

        payment_method = None

        if payment_method_id is not None:
            bill_pay_methd = BillingPaymentMethod.objects.filter(id=payment_method_id).first()
            if bill_pay_methd is not None and bill_pay_methd.payment_method == BillingPaymentMethod.PAYMENT_ACH:
                bank_account = BankAccount.objects.filter(billing_payment_method=bill_pay_methd).first()
                if bank_account:
                    payment_method = 'bank account %s ending with %s' % (bank_account.bank_name, bank_account.last4)
                else:
                    logger.exception('No bank account on file for subscription #%d.' % self.pk)
            elif bill_pay_methd is not None:
                card = Card.objects.filter(billing_payment_method=bill_pay_methd).first()
                if card:
                    payment_method = 'credit card ending with %s that expires on %s/%s' % (card.last4, card.exp_month, card.exp_year)
                else:
                    logger.exception('No credit card on file for subscription #%d.' % self.pk)
            else:
                logger.exception('No credit card on file for subscription #%d.' % self.pk)
        else:
            payment = self.account.get_default_payment()
            if payment is not None and  isinstance(payment, BankAccount):
                if not payment.verified:
                    payment_method = 'bank account %s ending with %s is not verified' % (payment.bank_name, payment.last4)
                else:
                    payment_method = 'bank account %s ending with %s' % (payment.bank_name, payment.last4)
            elif payment is not None and isinstance(payment, Card):
                payment_method = 'credit card ending with %s that expires on %s/%s' % (payment.last4, payment.exp_month, payment.exp_year)
            else:
                logger.exception('No credit card on file for subscription #%d.' % self.pk)
        context = {
            'payment_method': payment_method,
            'user': user,
        }

        send_html_email('emails/payment_failed', context, subject, settings.DEFAULT_FROM_EMAIL, [user.email])

    def send_subscription_reminder(self):
        subject = 'Rise Statement Available'

        user = self.account.primary_user
        payment_method = None
        payment_account = self.account.get_default_payment()

        if payment_account is None:
            payment_method = 'account does not have a credit card or bank account associated with it. Please add a new credit card or bank account, and this card/account'
        elif isinstance(payment_account, BankAccount):
            payment_method = 'bank account %s ending with %s' % (payment_account.bank_name, payment_account.last4)
        else:
            payment_method = 'credit card ending with %s that expires on %s/%s' % (payment_account.last4, payment_account.exp_month, payment_account.exp_year)

        context = {
            'subscription': self,
            'payment_method': payment_method,
            'user': user,
        }

        send_html_email('emails/subscription_reminder', context, subject, settings.DEFAULT_FROM_EMAIL, [user.email])

    def send_rise_notification_email(self, error_message):
        """
        Sends a notification of failed payment to Rise
        """
        subject = 'Subscription Payment Failed'

        context = {
            'error_message': error_message,
            'account': self.account,
        }

        send_html_email('emails/admin_payment_failed_notification', context, subject, settings.DEFAULT_FROM_EMAIL, settings.PAYMENT_FAILED_NOTIFICATION_LIST)


class Invoice(models.Model):
    """
    An invoice for an account

    account: The account this invoice is for
    stripe_id: The stripe id for this invoice
    amount_due: Final amount due at this time for this invoice.
    attempt_count: Number of payment attempts made for this invoice, from the perspective of the payment retry schedule.
    attempted: Whether or not an attempt has been made to pay the invoice. An invoice is not attempted until 1 hour
        after the invoice.created webhook, for example, so you might not want to display that invoice as unpaid to your users.
    closed: Whether or not the invoice is still trying to collect payment. An invoice is closed if it’s either paid or
        it has been marked closed. A closed invoice will no longer attempt to collect payment.
    paid: Whether or not payment was successfully collected for this invoice.
    forgiven: Whether or not the invoice has been forgiven. Forgiving an invoice instructs us to update the subscription
        status as if the invoice were succcessfully paid. Once an invoice has been forgiven, it cannot be unforgiven or reopened
    period_end: End of the usage period the invoice covers
    period_start: Start of the usage period the invoice covers
    subtotal: Total of all subscriptions, invoice items, and prorations on the invoice before any discount is applied
    total: Total after discount
    charge: ID of the latest charge generated for this invoice, if any.
    description: Description of this invoice
    next_payment_attempt: The time at which payment will next be attempted.
    """

    account = models.ForeignKey('accounts.Account', blank=True, null=True)
    stripe_id = models.CharField(max_length=64, db_index=True)
    amount_due = models.DecimalField(max_digits=10, decimal_places=2)
    attempt_count = models.PositiveIntegerField(default=0)
    attempted = models.BooleanField(default=False)
    closed = models.BooleanField(default=False)
    paid = models.BooleanField(default=False)
    forgiven = models.BooleanField(default=False)
    period_start = models.DateTimeField(blank=True, null=True)
    period_end = models.DateTimeField(blank=True, null=True)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    charge = models.ForeignKey('billing.Charge', on_delete=models.SET_NULL, null=True, blank=True, related_name='invoice_charges')
    description = models.CharField(max_length=256, blank=True, null=True)
    next_payment_attempt = models.DateTimeField(blank=True, null=True)

    objects = InvoiceManager()

    def get_stripe_invoice(self):
        """
        Returns the Stripe invoice object
        """

        return stripe.Invoice.retrieve(self.stripe_id)

    def update_from_stripe_invoice(self, stripe_invoice, account=None):
        """
        Updates the fields of this Invoice from the given stripe invoice
        If account is provided, account lookup based on stripe customer id is skipped.
        """
        self.stripe_id = stripe_invoice.id
        if account:
            self.account = account
        else:
            self.account = Account.objects.filter(stripe_customer_id=stripe_invoice.customer).first()

        self.amount_due = stripe_invoice.amount_due / Decimal('100')
        self.total = stripe_invoice.total / Decimal('100')
        self.subtotal = stripe_invoice.subtotal / Decimal('100')
        self.attempt_count = stripe_invoice.attempt_count
        self.attempted = stripe_invoice.attempted
        self.closed = stripe_invoice.closed
        self.paid = stripe_invoice.paid
        self.forgiven = stripe_invoice.forgiven
        self.period_start = convert_timestamp(stripe_invoice.period_start)
        self.period_end = convert_timestamp(stripe_invoice.period_end)
        self.next_payment_attempt = convert_timestamp(stripe_invoice.next_payment_attempt)
        if stripe_invoice.charge:
            charge = Charge.objects.filter(vault_id=stripe_invoice.charge).first()
            if charge is None:
                stripe_charge = stripe.Charge.retrieve("ch_14yVD045W9qtAigI1wUoXwHT")
                charge = Charge()
                charge.update_from_stripe_charge(stripe_charge)
                charge.save()
                self.charge = charge
            else:
                self.charge = charge

        self.description = stripe_invoice.description
        if self.charge and not self.charge.description:
            self.charge.description = stripe_invoice.description
            self.charge.save()

    def __unicode__(self):
        return self.stripe_id


class InvoiceLineItem(models.Model):
    """
    A line item for a given invoice

    account: The account to be charged.
    invoice: The associated invoice, or None if not associated with one yet
    stripe_id: The stripe id for this invoice item
    amount: the amount of this invoice item
    proration: Whether or not the invoice item was created automatically as a proration adjustment when the customer switched plans
    description: Description of this item
    """

    account = models.ForeignKey('accounts.Account', blank=True, null=True)
    invoice = models.ForeignKey('billing.Invoice', blank=True, null=True)
    stripe_id = models.CharField(max_length=64, db_index=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    proration = models.BooleanField(default=False)
    description = models.CharField(max_length=256)

    objects = InvoiceLineItemManager()

    def update_from_stripe_invoice_item(self, stripe_invoice_item, account=None):
        """
        Updates this invoice item's fields from the given stripe invoice item. Does NOT save to database.

        If account is provided, account lookup based on stripe customer id is skipped.
        """
        self.stripe_id = stripe_invoice_item.id

        if account:
            self.account = account
        else:
            self.account = Account.objects.get(stripe_customer_id=stripe_invoice_item.customer)

        if stripe_invoice_item.invoice:
            self.invoice = Invoice.objects.get(stripe_id=stripe_invoice_item.invoice)

        self.proration = stripe_invoice_item.proration

        self.amount = stripe_invoice_item.amount / Decimal('100')

        self.description = stripe_invoice_item.description

    def __unicode__(self):
        return self.stripe_id
