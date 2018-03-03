# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('reservations', '0012_auto_20141202_1501'),
    ]

    operations = [
        migrations.AddField(
            model_name='flightwaitlist',
            name='passenger_count',
            field=models.PositiveIntegerField(default=0),
            preserve_default=True,
        ),
    ]
