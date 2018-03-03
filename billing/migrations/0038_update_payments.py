from __future__ import unicode_literals
from django.db import migrations
from billing.models import Card,BillingPaymentMethod,BankAccount

def load_data(apps, schema_editor):
    cardlist = Card.objects.filter().all()
    for card in cardlist:
        bp = BillingPaymentMethod()
        bp.account = card.account
        bp.payment_method = BillingPaymentMethod.PAYMENT_CREDIT_CARD
        if card.account is not None and card.account.payment_method == BillingPaymentMethod.PAYMENT_CREDIT_CARD\
            and BillingPaymentMethod.objects.filter(account=bp.account,is_default=True).first() is None:
            bp.is_default = True
        else:
            bp.is_default = False
        bp.save()
        card.billing_payment_method = bp
        card.save()
    banklist = BankAccount.objects.filter().all()
    for bank in banklist:
        bp = BillingPaymentMethod()
        bp.account = bank.account
        bp.payment_method = BillingPaymentMethod.PAYMENT_ACH
        if bank.account is not None and bank.account.payment_method == BillingPaymentMethod.PAYMENT_ACH\
            and BillingPaymentMethod.objects.filter(account=bp.account,is_default=True).first() is None:
            bp.is_default = True
        else:
            bp.is_default = False
        bp.save()
        bank.billing_payment_method = bp
        bank.save()

class Migration(migrations.Migration):
    dependencies = [
        ('billing', '0037_auto_20160505_2156')
      ]

    operations = [
        migrations.RunPython(load_data)
    ]
