# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reservations', '0028_flightreservation_tax'),
    ]

    operations = [
        migrations.AddField(
            model_name='flightreservation',
            name='other_charges',
            field=models.DecimalField(default=0, max_digits=10, decimal_places=2),
        ),
    ]
