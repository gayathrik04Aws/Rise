# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0001_initial'),
        ('accounts', '0006_account_company_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='account',
            name='plan',
            field=models.ForeignKey(blank=True, to='billing.Plan', null=True),
            preserve_default=True,
        ),
    ]
