# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reservations', '0030_auto_20160216_1126'),
    ]

    operations = [
        migrations.AddField(
            model_name='flightreservation',
            name='final_adjusted_seat_cost',
            field=models.DecimalField(default=0, max_digits=10, decimal_places=2),
        ),
        migrations.AddField(
            model_name='flightreservation',
            name='final_adjusted_tax',
            field=models.DecimalField(default=0, max_digits=10, decimal_places=2),
        ),
    ]
