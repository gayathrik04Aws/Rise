# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('anywhere', '0017_anywhereflightrequest_seats_required'),
    ]

    operations = [
        migrations.AddField(
            model_name='anywhereflightset',
            name='seats_required',
            field=models.IntegerField(default=6, verbose_name=b'# Seats booked to confirm'),
        ),
    ]
