# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('reservations', '0025_auto_20150928_1554'),
    ]

    operations = [
        migrations.AlterField(
            model_name='flightreservation',
            name='date_cancelled',
            field=models.DateTimeField(null=True, blank=True),
        ),
    ]
