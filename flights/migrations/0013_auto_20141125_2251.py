# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('flights', '0012_merge'),
    ]

    operations = [
        migrations.AlterField(
            model_name='flightmessage',
            name='flight',
            field=models.ForeignKey(related_name='flight_flight_messages', on_delete=django.db.models.deletion.SET_NULL, blank=True, to='flights.Flight', null=True),
            preserve_default=True,
        ),
    ]
