# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('flights', '0010_auto_20141125_1618'),
    ]

    operations = [
        migrations.AddField(
            model_name='flightmessage',
            name='title',
            field=models.CharField(default='c', max_length=128),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='flightmessage',
            name='message_type',
            field=models.CharField(default=b'I', max_length=1, choices=[(b'I', b'Information'), (b'D', b'Delay'), (b'C', b'Cancellation')]),
            preserve_default=True,
        ),
    ]
