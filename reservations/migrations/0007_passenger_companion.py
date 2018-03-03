# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('reservations', '0006_auto_20141125_1313'),
    ]

    operations = [
        migrations.AddField(
            model_name='passenger',
            name='companion',
            field=models.BooleanField(default=False),
            preserve_default=True,
        ),
    ]
