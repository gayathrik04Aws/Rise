# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reservations', '0031_auto_20160216_1453'),
    ]

    operations = [
        migrations.AddField(
            model_name='flightreservation',
            name='cancellation_reason',
            field=models.CharField(max_length=50, null=True),
        ),
    ]
