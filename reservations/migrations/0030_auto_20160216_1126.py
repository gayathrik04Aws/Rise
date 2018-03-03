# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reservations', '0029_flightreservation_other_charges'),
    ]

    operations = [
        migrations.AddField(
            model_name='flightreservation',
            name='anywhere_refund_due',
            field=models.DecimalField(default=0, max_digits=10, decimal_places=2),
        ),
        migrations.AddField(
            model_name='flightreservation',
            name='anywhere_refund_paid',
            field=models.BooleanField(default=False),
        ),
    ]
