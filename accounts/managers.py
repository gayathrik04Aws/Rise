from django.db import models
from django.contrib.auth.models import BaseUserManager
from django.utils import timezone
from django.utils.crypto import get_random_string


class PaymentMethodManager(models.Manager):


    def create_payment_method(self,account,payment_method,nickname=None,is_default=False):

        return self.create(
            account=account,
            payment_method=payment_method,
            nickname=nickname,
            is_default=is_default
        )


class UserManager(BaseUserManager):
    """
    A custom user manager for creating users and superusers
    """

    def _create_user(self, email, first_name, last_name, password, is_staff, is_superuser, **extra_fields):
        """
        A private method to create the actual user
        """

        now = timezone.now()
        if not email:
            raise ValueError('The given email must be set')

        email = self.normalize_email(email)

        user = self.model(first_name=first_name, last_name=last_name, email=email, is_staff=is_staff, is_active=True, is_superuser=is_superuser, last_login=now, date_joined=now, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, first_name, last_name, password, **extra_fields):
        """
        Creates a user based on the given parameters
        """
        return self._create_user(email, first_name, last_name, password, False, False, **extra_fields)

    def create_superuser(self, email, first_name, last_name, password, **extra_fields):
        """
        Creates a super user based on the given parameters
        """
        return self._create_user(email, first_name, last_name, password, True, True, **extra_fields)


class InviteManager(models.Manager):
    """
    An invite manager that makes it easy to create new invites
    """

    ALLOWED_CHARS = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'

    def _generate_code(self, length=12):
        code = get_random_string(length, allowed_chars=InviteManager.ALLOWED_CHARS)
        while self.model.objects.filter(code=code).exists():
            code = get_random_string(length, allowed_chars=InviteManager.ALLOWED_CHARS)
        return code

    def create_physical_invites(self, user, count):
        """
        Create a `count` of physical invites for the given `user`.
        """

        invites = []

        for _ in range(count):
            invite = self.model(account=user.account, created_by=user, code=self._generate_code(length=6), invite_type=self.model.INVITE_TYPE_PHYSICAL)
            invite.save(using=self._db)
            invites.append(invite)

        return invites

    def create_digital_invite(self, user, email, origin_city=None, first_name=None, last_name=None, phone=None):
        """
        Creates and sends a digital invite for the given `user` to the given `email`.
        """
        account = None
        if user:
            account = user.account

        invite = self.model(account=account, created_by=user, code=self._generate_code(), invite_type=self.model.INVITE_TYPE_DIGITAL,
            email=email, origin_city=origin_city, first_name=first_name, last_name=last_name, phone=phone)
        invite.save(using=self._db)
        return invite
