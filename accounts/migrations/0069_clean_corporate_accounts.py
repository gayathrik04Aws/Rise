# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations
from accounts.models import Account
from billing.models import Plan


def load_data(apps, schema_editor):
    accounts = Account.objects.filter(status='A',account_type='C').all()
    plan = Plan.objects.filter(name='Executive').first()
    for acct in accounts:
        acct.plan=plan
        acct.contract=None
        acct.save()


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0068_merge')
      ]

    operations = [
        migrations.RunPython(load_data)
    ]
