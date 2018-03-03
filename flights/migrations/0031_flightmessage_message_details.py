# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('flights', '0030_auto_20150126_1610'),
    ]

    operations = [
        migrations.AddField(
            model_name='flightmessage',
            name='message_details',
            field=models.CharField(max_length=320, null=True, blank=True),
            preserve_default=True,
        ),
    ]
