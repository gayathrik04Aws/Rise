# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0060_billingpaymentmethod'),
        ('billing', '0036_auto_20160427_1028'),
    ]

    operations = [
        migrations.AddField(
            model_name='bankaccount',
            name='billing_payment_method',
            field=models.OneToOneField(null=True, to='accounts.BillingPaymentMethod'),
        ),
        migrations.AddField(
            model_name='card',
            name='billing_payment_method',
            field=models.OneToOneField(null=True, to='accounts.BillingPaymentMethod'),
        ),
        migrations.AlterField(
            model_name='bankaccount',
            name='account',
            field=models.ForeignKey(to='accounts.Account'),
        ),
        migrations.AlterField(
            model_name='card',
            name='account',
            field=models.ForeignKey(to='accounts.Account'),
        ),
    ]
