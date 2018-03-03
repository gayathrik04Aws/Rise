# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('flights', '0050_alertflightnotification'),
    ]

    operations = [
        migrations.AddField(
            model_name='airport',
            name='map_url',
            field=models.CharField(max_length=150, null=True, blank=True),
        ),
    ]
