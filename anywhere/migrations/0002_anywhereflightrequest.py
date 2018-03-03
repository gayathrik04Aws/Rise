# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0055_auto_20151027_1257'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('anywhere', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='AnywhereFlightRequest',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('is_round_trip', models.BooleanField(default=False, verbose_name=b'Flight is Round-Trip?')),
                ('depart_date', models.DateField(null=True, verbose_name=b'Departure Date')),
                ('depart_when', models.CharField(default=b'anytime', max_length=32, verbose_name=b'Departure Time of Day', choices=[(b'morning', b'Morning'), (b'afternoon', b'Afternoon'), (b'evening', b'Evening'), (b'anytime', b'Flexible')])),
                ('return_date', models.DateField(null=True, verbose_name=b'Returning Date')),
                ('return_when', models.CharField(default=b'anytime', max_length=32, verbose_name=b'Returning Time of Day', choices=[(b'morning', b'Morning'), (b'afternoon', b'Afternoon'), (b'evening', b'Evening'), (b'anytime', b'Flexible')])),
                ('seats', models.IntegerField(verbose_name=b'# Seats Requested')),
                ('created_by', models.ForeignKey(related_name='anywhere_flight_requests', on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL, null=True)),
                ('destination_city', models.ForeignKey(related_name='+', on_delete=django.db.models.deletion.SET_NULL, to='accounts.City', null=True)),
                ('origin_city', models.ForeignKey(related_name='+', on_delete=django.db.models.deletion.SET_NULL, to='accounts.City', null=True)),
                ('route', models.ForeignKey(related_name='anywhere_flight_requests', to='anywhere.AnywhereRoute', null=True)),
            ],
        ),
    ]
