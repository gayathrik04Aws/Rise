# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('reservations', '0008_auto_20141125_1602'),
    ]

    operations = [
        migrations.AlterField(
            model_name='passenger',
            name='flight_reservation',
            field=models.ForeignKey(related_name='passenger_flight_reservations', to='reservations.FlightReservation'),
            preserve_default=True,
        ),
    ]
