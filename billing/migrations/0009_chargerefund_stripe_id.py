# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0008_chargerefund'),
    ]

    operations = [
        migrations.AddField(
            model_name='chargerefund',
            name='stripe_id',
            field=models.CharField(max_length=64, null=True, blank=True),
            preserve_default=True,
        ),
    ]
