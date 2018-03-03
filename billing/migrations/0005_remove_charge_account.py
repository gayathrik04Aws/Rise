# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0004_auto_20141117_1616'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='charge',
            name='account',
        ),
    ]
