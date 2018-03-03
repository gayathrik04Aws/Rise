from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone

from optparse import make_option
import redis

from accounts.models import Account
from flights.models import Flight


class Command(BaseCommand):

    option_list = BaseCommand.option_list + (
        make_option('--refresh',
            action='store_true',
            dest='refresh',
            default=False,
            help='Refersh the cache if mismatch'),
    )

    def handle(self, *args, **options):
        """
        """
        r = redis.from_url(settings.REDIS_URL)
        refresh = options.get('refresh')

        flights = Flight.objects.filter(departure__gte=timezone.now())

        flight_cache_fields = ['seats_available']

        for flight in flights:
            mismatch = False

            for flight_cache_field in flight_cache_fields:
                cache_key = flight.cache_key(flight_cache_field)
                cache_value = r.get(cache_key)
                if cache_value is not None:
                    cache_value = int(cache_value)
                value = getattr(flight, flight_cache_field)

                if cache_value is not None and cache_value != value:
                    print 'flight %s %s : %s value "%s" != cache value "%s"' % (flight.id, flight.flight_number, flight_cache_field, value, cache_value)
                    mismatch = True

            if mismatch and refresh:
                flight.refresh_cache()

        accounts = Account.objects.all()

        account_cache_fields = ['available_passes', 'available_companion_passes', 'complimentary_passes', 'complimentary_companion_passes']

        for account in accounts:
            mismatch = False

            for account_cache_field in account_cache_fields:
                cache_key = account.get_cache_key(account_cache_field)
                cache_value = r.get(cache_key)
                if cache_value is not None:
                    cache_value = int(cache_value)
                value = getattr(account, account_cache_field)

                if cache_value is not None and cache_value != value:
                    print 'account %s %s : %s value "%s" != cache value "%s"' % (account.id, account.account_name(), account_cache_field, value, cache_value)
                    mismatch = True

            if mismatch and refresh:
                account.refresh_cache()
