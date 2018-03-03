# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0014_auto_20150129_1457'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='customer',
            name='account',
        ),
        migrations.RemoveField(
            model_name='bankaccount',
            name='customer',
        ),
        migrations.RemoveField(
            model_name='card',
            name='customer',
        ),
        migrations.RemoveField(
            model_name='charge',
            name='customer',
        ),
        migrations.RemoveField(
            model_name='invoice',
            name='customer',
        ),
        migrations.RemoveField(
            model_name='invoicelineitem',
            name='customer',
        ),
        migrations.RemoveField(
            model_name='subscription',
            name='customer',
        ),
        migrations.DeleteModel(
            name='Customer',
        ),
    ]
