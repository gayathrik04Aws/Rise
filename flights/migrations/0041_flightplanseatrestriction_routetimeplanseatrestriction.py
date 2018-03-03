# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0027_auto_20150526_1427'),
        ('flights', '0040_auto_20150930_1350'),
    ]

    operations = [
        migrations.CreateModel(
            name='FlightPlanSeatRestriction',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('seats', models.PositiveIntegerField(default=0)),
                ('flight', models.ForeignKey(to='flights.Flight')),
                ('plan', models.ForeignKey(to='billing.Plan')),
            ],
        ),
        migrations.CreateModel(
            name='RouteTimePlanSeatRestriction',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('seats', models.PositiveIntegerField(default=0)),
                ('plan', models.ForeignKey(to='billing.Plan')),
                ('route_time', models.ForeignKey(to='flights.RouteTime')),
            ],
        ),
    ]
