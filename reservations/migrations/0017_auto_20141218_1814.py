# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('reservations', '0016_flightpassengeraudittrail'),
    ]

    operations = [
        migrations.AddField(
            model_name='flightpassengeraudittrail',
            name='passenger_first_name',
            field=models.CharField(default='', max_length=30),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='flightpassengeraudittrail',
            name='passenger_last_name',
            field=models.CharField(default='', max_length=30),
            preserve_default=False,
        ),
    ]
