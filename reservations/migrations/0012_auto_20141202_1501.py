# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0007_remove_charge_invoice'),
        ('reservations', '0011_auto_20141202_1447'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='flightreservation',
            name='charge',
        ),
        migrations.AddField(
            model_name='reservation',
            name='charge',
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, to='billing.Charge', null=True),
            preserve_default=True,
        ),
    ]
