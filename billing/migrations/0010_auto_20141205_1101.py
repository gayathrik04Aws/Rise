# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0009_chargerefund_stripe_id'),
    ]

    operations = [
        migrations.AlterField(
            model_name='charge',
            name='amount_refunded',
            field=models.DecimalField(null=True, max_digits=10, decimal_places=2, blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='charge',
            name='card',
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, blank=True, to='billing.Card', null=True),
            preserve_default=True,
        ),
    ]
