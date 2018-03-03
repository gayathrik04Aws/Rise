# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0023_auto_20141128_1108'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='account',
            field=models.ForeignKey(related_name='account_users', on_delete=django.db.models.deletion.SET_NULL, blank=True, to='accounts.Account', null=True),
            preserve_default=True,
        ),
    ]
