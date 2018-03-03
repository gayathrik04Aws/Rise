# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import localflavor.us.models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0001_initial'),
        ('accounts', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('flights', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='FlightReservation',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('status', models.CharField(default=b'P', max_length=1, choices=[(b'P', b'Pending'), (b'R', b'Reserved'), (b'I', b'Checked-In'), (b'C', b'Cancelled'), (b'L', b'Complete')])),
                ('passenger_count', models.PositiveIntegerField(default=1)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL, null=True)),
                ('flight', models.ForeignKey(to='flights.Flight')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='FlightWaitlist',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('flight', models.ForeignKey(to='flights.Flight')),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Passenger',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('first_name', models.CharField(max_length=30)),
                ('last_name', models.CharField(max_length=30)),
                ('email', models.EmailField(unique=True, max_length=75)),
                ('phone', localflavor.us.models.PhoneNumberField(max_length=20)),
                ('date_of_birth', models.DateField()),
                ('background_status', models.PositiveIntegerField(default=0, choices=[(b'Not Started', 0), (b'Processing', 1), (b'Passed', 2), (b'Failed', 3)])),
                ('flight_reservation', models.ForeignKey(to='reservations.FlightReservation')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL, null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Reservation',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('status', models.CharField(default=b'P', max_length=1, choices=[(b'P', b'Pending'), (b'R', b'Reserved'), (b'C', b'Cancelled'), (b'L', b'Complete')])),
                ('cost', models.DecimalField(default=0, max_digits=10, decimal_places=2)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('account', models.ForeignKey(to='accounts.Account')),
                ('charge', models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, to='billing.Charge', null=True)),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL, null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='flightreservation',
            name='reservation',
            field=models.ForeignKey(to='reservations.Reservation'),
            preserve_default=True,
        ),
    ]
