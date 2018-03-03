# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0009_merge'),
    ]

    operations = [
        migrations.AddField(
            model_name='account',
            name='activated',
            field=models.DateTimeField(null=True, blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='account',
            name='status',
            field=models.CharField(default=b'P', max_length=1, choices=[(b'P', b'Pending'), (b'A', b'Active'), (b'S', b'Suspended'), (b'D', b'Delinquent')]),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='account',
            name='vip',
            field=models.BooleanField(default=False),
            preserve_default=True,
        ),
    ]
