# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='plan',
            name='reservations',
        ),
        migrations.AddField(
            model_name='plan',
            name='pass_count',
            field=models.PositiveIntegerField(default=2),
            preserve_default=True,
        ),
    ]
