# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime
from django.utils.timezone import utc


class Migration(migrations.Migration):

    dependencies = [
        ('reservations', '0017_auto_20141218_1814'),
    ]

    operations = [
        migrations.AddField(
            model_name='flightpassengeraudittrail',
            name='passenger_date_of_birth',
            field=models.DateField(default=datetime.datetime(2014, 12, 19, 0, 14, 26, 911705, tzinfo=utc)),
            preserve_default=False,
        ),
    ]
