# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0049_auto_20150729_0936'),
    ]

    operations = [
        migrations.AlterField(
            model_name='account',
            name='status',
            field=models.CharField(default=b'P', max_length=1, choices=[(b'P', b'Pending'), (b'A', b'Active'), (b'S', b'Suspended'), (b'V', b'Pending ACH Verification'), (b'C', b'Cancelled')]),
        ),
    ]
