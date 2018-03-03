import factory
from factory.django import DjangoModelFactory


class PlanFactory(DjangoModelFactory):
    class Meta:
        model = 'billing.Plan'

    name = factory.Sequence(lambda n: 'Plan %d' % n)
    amount = factory.Sequence(lambda n: n * 1000)
