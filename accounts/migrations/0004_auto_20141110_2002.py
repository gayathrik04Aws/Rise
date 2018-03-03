# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_auto_20140930_1851'),
    ]

    operations = [
        migrations.AddField(
            model_name='account',
            name='account_type',
            field=models.CharField(default=b'I', max_length=1, choices=[(b'I', b'Individual'), (b'C', b'Corporate')]),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='account',
            name='member_count',
            field=models.PositiveIntegerField(default=1),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='account',
            name='pass_count',
            field=models.PositiveIntegerField(default=2),
            preserve_default=True,
        ),
    ]
