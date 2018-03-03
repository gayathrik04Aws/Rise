# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('flights', '0005_auto_20141111_1609'),
    ]

    operations = [
        migrations.AddField(
            model_name='flight',
            name='flight_number',
            field=models.CharField(default='0000', max_length=16),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='routetime',
            name='flight_number',
            field=models.CharField(default='0000', max_length=16),
            preserve_default=False,
        ),
    ]
