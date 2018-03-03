# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('flights', '0034_auto_20150225_1559'),
    ]

    operations = [
        migrations.AddField(
            model_name='flightmessage',
            name='internal',
            field=models.BooleanField(default=False),
            preserve_default=True,
        ),
    ]
