# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('reservations', '0022_auto_20150717_1412'),
    ]

    operations = [
        migrations.AddField(
            model_name='flightwaitlist',
            name='status',
            field=models.CharField(default=b'W', max_length=1, choices=[(b'W', b'Waiting'), (b'R', b'Reserved'), (b'C', b'Cancelled')]),
        ),
    ]
