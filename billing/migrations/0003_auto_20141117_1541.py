# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0002_auto_20141112_2315'),
    ]

    operations = [
        migrations.AddField(
            model_name='subscription',
            name='canceled_at',
            field=models.DateTimeField(null=True, blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='subscription',
            name='current_period_end',
            field=models.DateTimeField(null=True, blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='subscription',
            name='current_period_start',
            field=models.DateTimeField(null=True, blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='subscription',
            name='ended_at',
            field=models.DateTimeField(null=True, blank=True),
            preserve_default=True,
        ),
    ]
