# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('reservations', '0010_auto_20141128_1320'),
    ]

    operations = [
        migrations.AlterField(
            model_name='passenger',
            name='flight_reservation',
            field=models.ForeignKey(to='reservations.FlightReservation'),
            preserve_default=True,
        ),
    ]
