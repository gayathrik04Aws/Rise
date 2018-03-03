# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0024_auto_20150302_1305'),
    ]

    operations = [
        migrations.AlterField(
            model_name='charge',
            name='bank_account',
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, blank=True, to='billing.BankAccount', null=True),
            preserve_default=True,
        ),
    ]
