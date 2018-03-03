# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models

def remove_account_contracts_from_corp(apps, schema_editor):
    # previous migration had a bug, added contracts to Corporate accounts that only have a plan for seating logic purposes.
    accounts = apps.get_model("accounts", "Account")
    for acct in accounts.objects.filter(account_type='C'):
        acct.contract_id=None
        acct.contract_start_date=None
        acct.contract_end_date=None
        acct.save()


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0035_plan_requires_contract'),
    ]

    operations = [
        migrations.RunPython(remove_account_contracts_from_corp),
    ]
