from django.core.management.base import BaseCommand

from datetime import date, timedelta

from accounts.models import Account,User
from billing.models import Subscription
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):

    def handle(self, *args, **options):
        """
        """
        past_due_subscriptions = Subscription.objects.filter(status=Subscription.SUBSCRIPTION_STATUS_PAST_DUE, account__status=Account.STATUS_ACTIVE)
        user = User.objects.filter(email=settings.SYSTEM_ADMIN_EMAIL).first()
        for subscription in past_due_subscriptions:
            try:
                subscription.bill(created_by=user)
            except Exception as e:
                logger.exception('subscription renew failed for %d'% subscription.id)
                logger.exception(e)
        yesterday = date.today() - timedelta(days=1)

        subscriptions = Subscription.objects.filter(period_end__lte=yesterday, status=Subscription.SUBSCRIPTION_STATUS_ACTIVE, account__status=Account.STATUS_ACTIVE)

        for subscription in subscriptions:
            try:
                subscription.bill(created_by=user)
            except Exception as e:
                logger.exception('subscription renew failed for %d'% subscription.id)
                logger.exception(e)
