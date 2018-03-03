# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0007_auto_20141111_1805'),
    ]

    operations = [
        migrations.AddField(
            model_name='account',
            name='companion_pass_count',
            field=models.PositiveIntegerField(default=2),
            preserve_default=True,
        ),
    ]
