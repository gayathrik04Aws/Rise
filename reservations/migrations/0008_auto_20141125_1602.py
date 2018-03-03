# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0007_remove_charge_invoice'),
        ('reservations', '0007_passenger_companion'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='reservation',
            name='charge',
        ),
        migrations.RemoveField(
            model_name='reservation',
            name='cost',
        ),
        migrations.AddField(
            model_name='flightreservation',
            name='charge',
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, to='billing.Charge', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='flightreservation',
            name='cost',
            field=models.DecimalField(default=0, max_digits=10, decimal_places=2),
            preserve_default=True,
        ),
    ]
