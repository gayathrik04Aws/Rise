# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('flights', '0041_flightplanseatrestriction_routetimeplanseatrestriction'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='flight',
            name='max_seats_chairman',
        ),
        migrations.RemoveField(
            model_name='flight',
            name='max_seats_executive',
        ),
        migrations.RemoveField(
            model_name='flight',
            name='max_seats_express',
        ),
        migrations.RemoveField(
            model_name='routetime',
            name='max_seats_chairman',
        ),
        migrations.RemoveField(
            model_name='routetime',
            name='max_seats_executive',
        ),
        migrations.RemoveField(
            model_name='routetime',
            name='max_seats_express',
        ),
    ]
