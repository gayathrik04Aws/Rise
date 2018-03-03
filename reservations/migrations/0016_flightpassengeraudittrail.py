# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('flights', '0026_auto_20141217_1307'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('reservations', '0015_auto_20141218_1316'),
    ]

    operations = [
        migrations.CreateModel(
            name='FlightPassengerAuditTrail',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('update_type', models.PositiveIntegerField(default=0, choices=[(0, b'Update Background Check Status')])),
                ('update_details', models.TextField(max_length=160)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, blank=True, to=settings.AUTH_USER_MODEL, null=True)),
                ('flight', models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, blank=True, to='flights.Flight', null=True)),
                ('passenger', models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, blank=True, to='reservations.Passenger', null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
