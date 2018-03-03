# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0019_auto_20150130_1444'),
    ]

    operations = [
        migrations.AddField(
            model_name='subscription',
            name='braintree_id',
            field=models.CharField(max_length=64, null=True, blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='subscription',
            name='plan',
            field=models.ForeignKey(blank=True, to='billing.Plan', null=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='subscription',
            name='stripe_id',
            field=models.CharField(max_length=64, null=True, blank=True),
            preserve_default=True,
        ),
    ]
