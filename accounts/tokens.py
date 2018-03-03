from django.contrib.auth.tokens import PasswordResetTokenGenerator

from datetime import date, timedelta


class InviteTokenGenerator(PasswordResetTokenGenerator):

    def _today(self):
        return date.today() + timedelta(days=14)

invite_token_generator = InviteTokenGenerator()
