# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0059_merge'),
    ]

    operations = [
        migrations.CreateModel(
            name='BillingPaymentMethod',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('payment_method', models.CharField(default=b'C', max_length=1, choices=[(b'C', b'Credit Card'), (b'A', b'ACH')])),
                ('nickname', models.CharField(max_length=10, null=True)),
                ('is_default', models.BooleanField(default=False)),
                ('account', models.ForeignKey(to='accounts.Account')),
            ],
        ),
    ]
