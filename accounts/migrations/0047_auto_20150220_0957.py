# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0046_merge'),
    ]

    operations = [
        migrations.AlterField(
            model_name='account',
            name='plan',
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, blank=True, to='billing.Plan', null=True),
            preserve_default=True,
        ),
    ]
