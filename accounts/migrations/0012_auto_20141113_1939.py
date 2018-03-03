# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0011_account_corporate_amount'),
    ]

    operations = [
        migrations.AddField(
            model_name='account',
            name='available_companion_passes',
            field=models.PositiveIntegerField(default=0),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='account',
            name='available_passes',
            field=models.PositiveIntegerField(default=0),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='account',
            name='complimentary_companion_passes',
            field=models.PositiveIntegerField(default=0),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='account',
            name='complimentary_passes',
            field=models.PositiveIntegerField(default=0),
            preserve_default=True,
        ),
    ]
