
from __future__ import division
from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import date
import arrow
import stripe
stripe.api_key = settings.STRIPE_API_KEY


class CardManager(models.Manager):
    """
    A simple manager for cards
    """

    def create_from_braintree_card(self, account, braintree_card,payment_method):
        """
        Creates a new Card object from the given braintree card object
        """
        return self.create(
            account=account,
            token=braintree_card.token,
            last4=braintree_card.last_4,
            brand=braintree_card.card_type,
            exp_month=braintree_card.expiration_month,
            exp_year=braintree_card.expiration_year,
            billing_payment_method=payment_method
        )

    def create_from_stripe_card(self, account, stripe_card):
        """
        Create a local copy of the given stripe card for the given customer
        """
        return self.create(
            account=account,
            token=stripe_card.id,
            last4=stripe_card.last4,
            brand=stripe_card.brand,
            exp_month=stripe_card.exp_month,
            exp_year=stripe_card.exp_year,
        )


class ChargeManager(models.Manager):
    """
    A Simple manager for Charges
    """

    def create_from_braintree_transaction(self, transaction, account, card, description, created_by=None):
        return self.create(
            account=account,
            card=card,
            payment_method=self.model.PAYMENT_METHOD_CARD,
            vault_id=transaction.id,
            amount=transaction.amount,
            description=description,
            status=transaction.status,
            created=timezone.now(),
            created_by=created_by,
        )

    def create_from_stripe_payment(self, payment, account, bank_account, description, created_by=None):
        return self.create(
            account=account,
            bank_account=bank_account,
            payment_method=self.model.PAYMENT_METHOD_BANK,
            vault_id=payment.id,
            amount=(payment.amount / 100),
            description=description,
            status=payment.status,
            created=timezone.now(),
            created_by=created_by,
        )


class SubscriptionManager(models.Manager):
    """
    A simple manager for subscriptions
    """

    def get_current_subscriptions(self, account):
        """
        Returns active subscriptions for this account
        """
        # RISE 472 - Add pending payment status to this list, as this is technically "current" just not active.
        return self.get_queryset().filter(account=account, status__in=(self.model.SUBSCRIPTION_STATUS_ACTIVE, self.model.SUBSCRIPTION_STATUS_PAST_DUE, self.model.SUBSCRIPTION_STATUS_PENDING_PAYMENT))

    def create_subscription(self, account, start_date=None, created_by=None, override_amount=None,payment_method_id=None):
        """
        Creates a subscription for the given account

        start_date: When the subscription should start billing
        """

        if override_amount is not None:
            amount = override_amount
        else:
            amount = account.subscription_amount

        if account.is_corporate():
            description = '%s Subscription' % (account.account_name(),)
        else:
            description = '%s Subscription' % (account.plan.name,)


        if amount is None:
            amount = 0

        today = date.today()
        if start_date is not None:
            if start_date < today:
                start = today
            else:
                start = start_date
        else:
            start = today

        billing_day_of_month = start.day

        subscription = self.model(account=account, description=description, amount=amount, period_start=start, billing_day_of_month=billing_day_of_month, created_by=created_by)

        subscription.period_end = arrow.get(subscription.get_next_date(start)).replace(days=-1).date()

        subscription.save()

        # ensure account is active and not pending ACH setup
        if start == today and account.is_active():
            subscription.bill(payment_method_id=payment_method_id,created_by=created_by)

        return subscription


class InvoiceManager(models.Manager):
    """
    A manager for Invoices
    """

    def create_stripe_invoice(self, customer, pay=False):
        """
        Creates a stripe invoice and saves it locally

        customer: the customer to create the invoice for
        pay: if this invoice should be paid immediately
        """
        stripe_invoice = stripe.Invoice.create(customer=customer.stripe_id)

        invoice = self.model()
        invoice.update_from_stripe_invoice(stripe_invoice, customer=customer)
        invoice.save()

        if pay:
            stripe_invoice.pay()

        return invoice


class InvoiceLineItemManager(models.Manager):
    """
    A manager to enable creating a local and Stripe invoice line item
    """

    def create_stripe_invoice_line_item(self, customer, amount, description):
        """
        Creates an invoice line item in Stripe and saves it locally.

        Returns the local invoice line item model
        """

        stripe_invoice_item = stripe.InvoiceItem.create(
            customer=customer.stripe_id,
            amount=int(amount * 100),
            currency='usd',
            description=description)

        return self.create(stripe_id=stripe_invoice_item.id, customer=customer, amount=amount, description=description)
