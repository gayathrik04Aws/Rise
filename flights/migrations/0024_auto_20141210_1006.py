# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('flights', '0023_auto_20141203_1704'),
    ]

    operations = [
        migrations.AddField(
            model_name='routetime',
            name='max_seats_companion',
            field=models.PositiveIntegerField(default=4, help_text=b'How many seats may be reserved for Companion users', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='routetime',
            name='max_seats_corporate',
            field=models.PositiveIntegerField(default=4, help_text=b'How many seats may be reserved for Corporate users', null=True),
            preserve_default=True,
        ),
    ]
