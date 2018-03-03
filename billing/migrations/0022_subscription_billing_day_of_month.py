# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0021_auto_20150206_1023'),
    ]

    operations = [
        migrations.AddField(
            model_name='subscription',
            name='billing_day_of_month',
            field=models.PositiveIntegerField(default=1),
            preserve_default=True,
        ),
    ]
