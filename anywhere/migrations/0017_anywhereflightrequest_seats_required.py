# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('anywhere', '0016_insert_group'),
    ]

    operations = [
        migrations.AddField(
            model_name='anywhereflightrequest',
            name='seats_required',
            field=models.IntegerField(default=6, verbose_name=b'# Seats Booked To Confirm'),
        ),
    ]
