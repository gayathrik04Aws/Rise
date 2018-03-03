from django.core.management.base import BaseCommand
from django.utils.crypto import get_random_string

from optparse import make_option

from accounts.models import Invite


class Command(BaseCommand):

    option_list = BaseCommand.option_list + (
        make_option('--sets',
            action='store',
            dest='sets',
            default=300,
            type='int',
            help='The number of invite code sets to generate'),

        make_option('--count',
            action='store',
            dest='count',
            default=5,
            type='int',
            help='Number of invite codes per set'),
    )

    def handle(self, *args, **options):
        """
        """

        PREFIX_CHARS = 'ABCDEFGHJKLMNPQRSTUVWXYZ'
        SUFFIX_CHARS = '23456789'

        prefixes = []
        codes = []

        # generate a list of prefixes
        for x in range(options.get('sets')):
            while True:
                prefix = get_random_string(3, allowed_chars=PREFIX_CHARS)
                # if we have already generated this prefix this session, try again
                if prefix in prefixes:
                    continue
                # if there are invite codes that already start with this prefix, try again
                if Invite.objects.filter(code__startswith=prefix).exists():
                    continue

                # prefix is good, add it to the list and break out of while loop
                prefixes.append(prefix)
                break

        for prefix in prefixes:
            for x in range(options.get('count')):
                while True:
                    suffix = get_random_string(3, allowed_chars=SUFFIX_CHARS)
                    code = '%s%s' % (prefix, suffix)

                    # if we already generated this code, try again
                    if code in codes:
                        continue

                    # if this code already exists, try again
                    if Invite.objects.filter(code=code).exists():
                        continue

                    # create the invite, add the code to the list and break out of while loop
                    Invite.objects.create(code=code, invite_type=Invite.INVITE_TYPE_PHYSICAL)
                    codes.append(code)
                    print code
                    break
