# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('flights', '0028_auto_20141222_1613'),
    ]

    operations = [
        migrations.AlterField(
            model_name='flightmessage',
            name='message',
            field=models.CharField(max_length=160),
            preserve_default=True,
        ),
    ]
