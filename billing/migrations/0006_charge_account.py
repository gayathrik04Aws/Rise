# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0014_merge'),
        ('billing', '0005_remove_charge_account'),
    ]

    operations = [
        migrations.AddField(
            model_name='charge',
            name='account',
            field=models.ForeignKey(blank=True, to='accounts.Account', null=True),
            preserve_default=True,
        ),
    ]
