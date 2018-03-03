# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('flights', '0008_auto_20141118_1938'),
    ]

    operations = [
        migrations.AddField(
            model_name='route',
            name='name',
            field=models.CharField(default='Route', max_length=128),
            preserve_default=False,
        ),
    ]
