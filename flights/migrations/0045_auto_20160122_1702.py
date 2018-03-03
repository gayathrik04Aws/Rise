# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('flights', '0044_auto_20160121_1226'),
    ]

    operations = [
        migrations.AddField(
            model_name='anywhereflightdetails',
            name='other_cost',
            field=models.DecimalField(default=0, max_digits=10, decimal_places=2),
        ),
        migrations.AddField(
            model_name='anywhereflightdetails',
            name='other_cost_desc',
            field=models.TextField(max_length=100, null=True, blank=True),
        ),
    ]
