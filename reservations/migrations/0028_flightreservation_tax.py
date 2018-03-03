# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reservations', '0027_auto_20160128_1355'),
    ]

    operations = [
        migrations.AddField(
            model_name='flightreservation',
            name='tax',
            field=models.DecimalField(default=0, max_digits=10, decimal_places=2),
        ),
    ]
