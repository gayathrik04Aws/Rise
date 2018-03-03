# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0011_plan_description'),
    ]

    operations = [
        migrations.AddField(
            model_name='plan',
            name='corporate_plan',
            field=models.BooleanField(default=False),
            preserve_default=True,
        ),
    ]
