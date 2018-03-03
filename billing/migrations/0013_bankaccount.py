# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0042_auto_20150114_1444'),
        ('billing', '0012_plan_corporate_plan'),
    ]

    operations = [
        migrations.CreateModel(
            name='BankAccount',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('stripe_id', models.CharField(max_length=64, db_index=True)),
                ('bank_name', models.CharField(max_length=128)),
                ('last4', models.CharField(max_length=4)),
                ('routing_number', models.CharField(max_length=32)),
                ('verified', models.BooleanField(default=False)),
                ('account', models.ForeignKey(to='accounts.Account')),
                ('customer', models.ForeignKey(to='billing.Customer')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
