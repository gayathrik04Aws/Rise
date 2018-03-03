# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('reservations', '0002_auto_20141120_2253'),
    ]

    operations = [
        migrations.AlterField(
            model_name='passenger',
            name='flight_reservation',
            field=models.ForeignKey(related_name='passenger_flight_reservation', to='reservations.FlightReservation'),
            preserve_default=True,
        ),
    ]
