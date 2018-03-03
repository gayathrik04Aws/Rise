# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('flights', '0033_auto_20150205_1312'),
    ]

    operations = [
        migrations.AlterField(
            model_name='flightmessage',
            name='message',
            field=models.CharField(max_length=256),
            preserve_default=True,
        ),
    ]
