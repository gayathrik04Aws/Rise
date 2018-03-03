import factory
from factory.django import DjangoModelFactory

from .models import Account


class UserFactory(DjangoModelFactory):

    class Meta:
        model = 'accounts.User'

    first_name = factory.Sequence(lambda n: 'User%d' % n)
    last_name = 'LastName'
    email = factory.LazyAttribute(lambda obj: '%s@email.com' % obj.first_name)

    @factory.post_generation
    def setuser_password(obj, create, extracted, **kwargs):
        obj.set_password('password')
        obj.save()


class AccountFactory(DjangoModelFactory):

    class Meta:
        model = 'accounts.Account'


class CorporateAccountFactory(AccountFactory):

    account_type = Account.TYPE_CORPORATE
    company_name = 'Acme Corp'
    corporate_amount = 16000
    member_count = 5
    pass_count = 10
    companion_pass_count = 0
    available_passes = 10


class StaffUserFactory(UserFactory):
    is_staff = True
