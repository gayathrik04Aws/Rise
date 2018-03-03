# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0022_subscription_billing_day_of_month'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='plan',
            name='corporate_plan',
        ),
        migrations.AlterField(
            model_name='subscription',
            name='status',
            field=models.CharField(default=b'active', max_length=16, choices=[(b'active', b'Acitve'), (b'past_due', b'Past Due'), (b'canceled', b'Cancelled'), (b'pending', b'Pending Payment')]),
            preserve_default=True,
        ),
    ]
