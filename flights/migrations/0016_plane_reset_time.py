# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime


class Migration(migrations.Migration):

    dependencies = [
        ('flights', '0015_merge'),
    ]

    operations = [
        migrations.AddField(
            model_name='plane',
            name='reset_time',
            field=models.TimeField(default=datetime.time(0, 0)),
            preserve_default=True,
        ),
    ]
