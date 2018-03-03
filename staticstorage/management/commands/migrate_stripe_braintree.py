from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

import arrow
import braintree
import stripe
stripe.api_key = settings.STRIPE_API_KEY

from accounts.models import Account,BillingPaymentMethod
from billing.models import Card


class Command(BaseCommand):
    """
    Management command to migrate accounts with stripe customer id's to braintree customer id's.
    """
    help = 'Migrates accounts with stripe_customer_id numbers to braintree_customer_id numbers'

    def handle(self, *args, **options):
        start_time = arrow.now().datetime
        self.stdout.write('Script start time: %s' % start_time)
        self.stdout.write('\tRetrieving accounts...\n')

        accounts = Account.objects.filter(braintree_customer_id__isnull=True,stripe_customer_id__isnull=False)
        updated = 0
        for account in accounts:
            stripe = account.stripe_customer_id

            try:
                braintree_customer = braintree.Customer.find(stripe)
                account.braintree_customer_id = braintree_customer.id
                account.save(update_fields=['braintree_customer_id'])
                self.stdout.write('\tUpdated customer id for account %d' % account.pk)

                braintree_card = braintree_customer.credit_cards[0]
                Card.objects.filter(account=account).delete()  # delete any stripe cards
                billing_payment_method = BillingPaymentMethod.objects.create_payment_method(account,'Card')
                Card.objects.create_from_braintree_card(account, braintree_card,billing_payment_method)
                updated += 1
            except braintree.exceptions.not_found_error.NotFoundError:
                self.stdout.write("\t[Warning] Couldn't find a match for account %d using stripe id %s. No changes will be made." % (account.pk, stripe))

        end_time = arrow.now().datetime
        self.stdout.write('\n\tFinished updating %d accounts.\n' % (updated))
        self.stdout.write('Script end time: %s' % (end_time))
