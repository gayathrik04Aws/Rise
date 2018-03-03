# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reservations', '0032_flightreservation_cancellation_reason'),
    ]

    operations = [
        migrations.AlterField(
            model_name='flightreservation',
            name='status',
            field=models.CharField(default=b'P', max_length=1, choices=[(b'P', b'Pending'), (b'A', b'Anywhere - Pending Confirmation'), (b'R', b'Reserved'), (b'I', b'Checked-In'), (b'C', b'Cancelled'), (b'L', b'Complete'), (b'N', b'No-Show'), (b'Q', b'Partial No-Show')]),
        ),
        migrations.AlterField(
            model_name='flightwaitlist',
            name='status',
            field=models.CharField(default=b'W', max_length=1, choices=[(b'W', b'Waiting'), (b'R', b'Reserved'), (b'C', b'Cancelled'), (b'E', b'Expired')]),
        ),
    ]
