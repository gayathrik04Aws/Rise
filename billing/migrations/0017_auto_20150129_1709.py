# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0016_auto_20150129_1520'),
    ]

    operations = [
        migrations.RenameField(
            model_name='charge',
            old_name='stripe_id',
            new_name='vault_id',
        ),
        migrations.AddField(
            model_name='charge',
            name='bank_account',
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, to='billing.BankAccount', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='charge',
            name='status',
            field=models.CharField(max_length=64, null=True, blank=True),
            preserve_default=True,
        ),
    ]
