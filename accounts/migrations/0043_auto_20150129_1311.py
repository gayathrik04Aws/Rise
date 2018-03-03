# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0042_auto_20150114_1444'),
    ]

    operations = [
        migrations.AlterField(
            model_name='account',
            name='payment_method',
            field=models.CharField(default=b'C', max_length=1, choices=[(b'C', b'Credit Card'), (b'A', b'ACH'), (b'M', b'Manual')]),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='account',
            name='status',
            field=models.CharField(default=b'P', max_length=1, choices=[(b'P', b'Pending'), (b'A', b'Active'), (b'S', b'Suspended'), (b'D', b'Delinquent'), (b'V', b'Pending ACH Verification')]),
            preserve_default=True,
        ),
    ]
