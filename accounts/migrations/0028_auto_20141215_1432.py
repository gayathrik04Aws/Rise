# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0027_userprofile_origin_airport'),
    ]

    operations = [
        migrations.AlterField(
            model_name='invite',
            name='account',
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, blank=True, to='accounts.Account', null=True),
            preserve_default=True,
        ),
    ]
