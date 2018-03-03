# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0064_merge'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userprofile',
            name='account',
            field=models.ForeignKey(related_name='userprofile_account', on_delete=django.db.models.deletion.SET_NULL, blank=True, to='accounts.Account', null=True),
        ),
    ]
