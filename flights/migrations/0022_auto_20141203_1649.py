# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('flights', '0021_flightmessage_created'),
    ]

    operations = [
        migrations.AlterField(
            model_name='flightplanrestriction',
            name='flight',
            field=models.ForeignKey(related_name='flight_plan_restrictions', to='flights.Flight'),
            preserve_default=True,
        ),
    ]
