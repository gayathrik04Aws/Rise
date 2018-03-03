# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0024_auto_20141201_1451'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='account',
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, blank=True, to='accounts.Account', null=True),
            preserve_default=True,
        ),
    ]
