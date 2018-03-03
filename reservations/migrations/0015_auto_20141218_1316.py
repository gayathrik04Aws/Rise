# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('reservations', '0014_auto_20141203_1327'),
    ]

    operations = [
        migrations.AlterField(
            model_name='flightreservation',
            name='flight',
            field=models.ForeignKey(to='flights.Flight'),
            preserve_default=True,
        ),
    ]
