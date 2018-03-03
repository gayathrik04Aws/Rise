from django.views.generic import View
from django.conf import settings
from django.http import HttpResponse

import json
from stripe.resource import convert_to_stripe_object
import logging
import braintree

from .models import Invoice, InvoiceLineItem, Charge, Subscription
from accounts.mixins import CsrfExemptMixin

logger = logging.getLogger(__name__)


class StripeWebhookView(CsrfExemptMixin, View):
    """
    A view to process webhooks from Stripe
    """

    def post(self, request, *args, **kwargs):
        event_data = json.loads(request.body)

        event = convert_to_stripe_object(event_data, settings.STRIPE_API_KEY)

        # if production and not a live event, ignore it
        if settings.PRODUCTION and not event.livemode:
            return HttpResponse()

        # converts the event type "charge.succeeded" into a method name "_charge_succeeded"
        type_parts = event.type.split('.')
        type_parts.insert(0, '')
        method_name = '_'.join(type_parts)

        # see if that method exists, and if callable, call it
        method = getattr(self, method_name, None)
        if callable(method):
            method(event)

        # successfully handle this webhook
        return HttpResponse()

    def _ping(self, event):
        """
        A ping event can be sent by stripe at any time to see if this webhook is responding
        """
        pass

    def _invoiceitem_created(self, event):
        """
        Occurs whenever an invoice item is created.
        """
        stripe_invoice_item = event.data.object

        # if this is not an invoice item we already created, save it
        if not InvoiceLineItem.objects.filter(stripe_id=stripe_invoice_item.id).exists():
            invoice_item = InvoiceLineItem()
            invoice_item.update_from_stripe_invoice_item(stripe_invoice_item)
            invoice_item.save()

    def _invoiceitem_updated(self, event):
        """
        Occurs whenever an invoice item is updated.
        """
        stripe_invoice_item = event.data.object

        # try and find the existing invoice item
        invoice_item = next(iter(InvoiceLineItem.objects.filter(stripe_id=stripe_invoice_item.id)), None)

        # if not found, create a new one
        if invoice_item is None:
            invoice_item = InvoiceLineItem()

        # update the invoice item and save it
        invoice_item.update_from_stripe_invoice_item(stripe_invoice_item)
        invoice_item.save()

    def _invoice_payment_failed(self, event):
        """
        Occurs whenever an invoice attempts to be paid, and the payment fails. This can occur either due to a declined
        payment, or because the customer has no active card.
        """
        pass

    def _invoice_payment_succeeded(self, event):
        """
        Occurs whenever an invoice attempts to be paid, and the payment succeeds.
        """
        stripe_invoice = event.data.object

        invoice = next(iter(Invoice.objects.filter(stripe_id=stripe_invoice.id)), None)

        if invoice is None:
            invoice = Invoice()

        invoice.update_from_stripe_invoice(stripe_invoice)

        invoice.save()

    def _invoice_updated(self, event):
        """
        Occurs whenever an invoice changes (for example, the amount could change).
        """
        stripe_invoice = event.data.object

        invoice = next(iter(Invoice.objects.filter(stripe_id=stripe_invoice.id)), None)

        if invoice is None:
            invoice = Invoice()

        invoice.update_from_stripe_invoice(stripe_invoice)

        invoice.save()

    def _invoice_created(self, event):
        """
        Occurs whenever a new invoice is created. If you are using webhooks, Stripe will wait one hour after they have
        all succeeded to attempt to pay the invoice; the only exception here is on the first invoice, which gets created
        and paid immediately when you subscribe a customer to a plan. If your webhooks do not all respond successfully,
        Stripe will continue retrying the webhooks every hour and will not attempt to pay the invoice. After 3 days,
        Stripe will attempt to pay the invoice regardless of whether or not your webhooks have succeeded.
        """
        stripe_invoice = event.data.object

        invoice = next(iter(Invoice.objects.filter(stripe_id=stripe_invoice.id)), None)

        if invoice is None:
            invoice = Invoice()

        invoice.update_from_stripe_invoice(stripe_invoice)

        invoice.save()

    def _charge_succeeded(self, event):
        """
        Occurs whenever a new charge is created and is successful.
        """
        stripe_charge = event.data.object

        charge = next(iter(Charge.objects.filter(vault_id=stripe_charge.id)), None)

        if charge is None:
            charge = Charge()

        charge.update_from_stripe_charge(stripe_charge)

        charge.save()
        try:
            charge.send_receipt_email()
        except Exception, e:
            logger.exception(e)

    def _charge_failed(self, event):
        """
        Occurs whenever a failed charge attempt occurs.
        """
        stripe_charge = event.data.object

        charge = next(iter(Charge.objects.filter(vault_id=stripe_charge.id)), None)

        if charge is None:
            charge = Charge()

        charge.update_from_stripe_charge(stripe_charge)

        charge.save()

    def _charge_refunded(self, event):
        """
        Occurs whenever a charge is refunded, including partial refunds.
        """
        stripe_charge = event.data.object

        charge = next(iter(Charge.objects.filter(vault_id=stripe_charge.id)), None)

        if charge is None:
            charge = Charge()

        charge.update_from_stripe_charge(stripe_charge)

        charge.save()

    def _charge_captured(self, event):
        """
        Occurs whenever a previously uncaptured charge is captured.
        """
        stripe_charge = event.data.object

        charge = next(iter(Charge.objects.filter(vault_id=stripe_charge.id)), None)

        if charge is None:
            charge = Charge()

        charge.update_from_stripe_charge(stripe_charge)

        charge.save()

    def _charge_updated(self, event):
        """
        Occurs whenever a charge description or metadata is updated.
        """
        stripe_charge = event.data.object

        charge = next(iter(Charge.objects.filter(vault_id=stripe_charge.id)), None)

        if charge is None:
            charge = Charge()

        charge.update_from_stripe_charge(stripe_charge)

        charge.save()

    # def _customer_subscription_updated(self, event):
    #     """
    #     Occurs whenever a subscription changes. Examples would include switching from one plan to another, or switching
    #     status from trial to active.
    #     """
    #     stripe_subscription = event.data.object
    #
    #     subscription = Subscription.objects.get(stripe_id=stripe_subscription.id)
    #
    #     subscription.update_from_stripe_subscription(stripe_subscription)
    #
    #     subscription.save()

    def _payment_created(self, event):
        """
        Occurs when a ACH payment is created
        """
        pass

    def _payment_failed(self, event):
        """
        Occurs when an ACH payment fails
        """
        payment = event.data.object

        charge = next(iter(Charge.objects.filter(vault_id=payment.id)), None)
        charge.update_from_stripe_charge(payment)
        charge.save()

        if charge.subscription is not None:
            if charge.subscription.status == Subscription.SUBSCRIPTION_STATUS_PENDING_PAYMENT:
                charge.subscription.send_payment_failed_email()
                charge.subscription.send_rise_notification_email(charge.failure_message)
                charge.subscription.status = Subscription.SUBSCRIPTION_STATUS_PAST_DUE
                charge.subscription.save()
        else:
            charge.send_rise_notification_email()

    def _payment_paid(self, event):
        """
        Occurs when an ACH payment is successful
        """
        payment = event.data.object

        charge = next(iter(Charge.objects.filter(vault_id=payment.id)), None)

        charge.update_from_stripe_charge(payment)

        charge.save()

        # update status of subscription if associated with one
        if charge.subscription is not None and charge.subscription.status == Subscription.SUBSCRIPTION_STATUS_PENDING_PAYMENT:
            charge.subscription.status = Subscription.SUBSCRIPTION_STATUS_ACTIVE
            charge.subscription.save()


class BraintreeWebhookView(CsrfExemptMixin, View):
    """
    A view to process webhooks from Braintree
    """

    def get(self, request, *args, **kwargs):
        bt_challenge = request.GET.get('bt_challenge')
        notification = braintree.WebhookNotification.verify(bt_challenge)
        return HttpResponse(notification)

    def post(self, request, *args, **kwargs):
        bt_signature = request.POST.get('bt_signature')
        bt_payload = request.POST.get('bt_payload')

        webhook_notification = braintree.WebhookNotification.parse(bt_signature, bt_payload)

        webhook_notification.kind
        # => "subscription_went_past_due"

        webhook_notification.timestamp
        # => Sun Jan 1 00:00:00 UTC 2012

        webhook_notification.subscription.id
        # => "subscription_id"

        return HttpResponse()
