from django.core.management.base import BaseCommand

from datetime import date, timedelta

from billing.models import Subscription
from accounts.models import Account


class Command(BaseCommand):

    def handle(self, *args, **options):
        """
        """
        today = date.today()
        auto_end = today + timedelta(days=6)
        manual_end = today + timedelta(days=13)

        manual_subscriptions = Subscription.objects.filter(account__status=Account.STATUS_ACTIVE, status=Subscription.SUBSCRIPTION_STATUS_ACTIVE, account__payment_method=Account.PAYMENT_MANUAL, period_end=manual_end)
        auto_subscriptions = Subscription.objects.filter(account__status=Account.STATUS_ACTIVE, status=Subscription.SUBSCRIPTION_STATUS_ACTIVE, period_end=auto_end).exclude(account__payment_method=Account.PAYMENT_MANUAL)

        for subscription in manual_subscriptions:
            subscription.send_subscription_reminder()

        for subscription in auto_subscriptions:
            subscription.send_subscription_reminder()
