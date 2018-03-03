# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime


class Migration(migrations.Migration):

    dependencies = [
        ('flights', '0020_auto_20141126_1552'),
    ]

    operations = [
        migrations.AddField(
            model_name='flightmessage',
            name='created',
            field=models.DateTimeField(default=datetime.datetime(2014, 11, 28, 12, 26, 40, 21290), auto_now_add=True),
            preserve_default=False,
        ),
    ]
