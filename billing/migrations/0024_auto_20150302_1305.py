# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0023_auto_20150220_0951'),
    ]

    operations = [
        migrations.AlterField(
            model_name='subscription',
            name='status',
            field=models.CharField(default=b'active', max_length=16, choices=[(b'active', b'Active'), (b'past_due', b'Past Due'), (b'canceled', b'Cancelled'), (b'pending', b'Pending Payment')]),
            preserve_default=True,
        ),
    ]
