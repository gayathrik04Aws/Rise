# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('reservations', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='flightreservation',
            name='flight',
            field=models.ForeignKey(related_name='flight_flight_reservations', to='flights.Flight'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='passenger',
            name='background_status',
            field=models.PositiveIntegerField(default=0, choices=[(0, b'Not Started'), (1, b'Processing'), (2, b'Passed'), (3, b'Failed')]),
            preserve_default=True,
        ),
    ]
