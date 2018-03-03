# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0033_plancontractprice'),
        ('accounts', '0056_account_do_not_charge'),
    ]

    operations = [
        migrations.AddField(
            model_name='account',
            name='contract',
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, blank=True, to='billing.PlanContractPrice', null=True),
        ),
        migrations.AddField(
            model_name='account',
            name='contract_end_date',
            field=models.DateTimeField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='account',
            name='contract_start_date',
            field=models.DateTimeField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='account',
            name='do_not_renew',
            field=models.BooleanField(default=False),
        ),
    ]
