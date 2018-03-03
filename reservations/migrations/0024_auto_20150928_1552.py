# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('reservations', '0023_flightwaitlist_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='flightreservation',
            name='cancelled_by',
            field=models.ForeignKey(related_name='cancelled_flight_reservations', on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL, null=True),
        ),
        migrations.AddField(
            model_name='flightreservation',
            name='date_cancelled',
            field=models.DateTimeField(null=True),
        ),
    ]
