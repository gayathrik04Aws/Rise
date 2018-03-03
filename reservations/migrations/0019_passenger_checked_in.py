# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('reservations', '0018_flightpassengeraudittrail_passenger_date_of_birth'),
    ]

    operations = [
        migrations.AddField(
            model_name='passenger',
            name='checked_in',
            field=models.BooleanField(default=False),
            preserve_default=True,
        ),
    ]
