# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0060_auto_20160518_1436'),
    ]

    operations = [
        migrations.AddField(
            model_name='account',
            name='contract_signature',
            field=models.CharField(max_length=50, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='account',
            name='contract_signeddate',
            field=models.DateTimeField(null=True, blank=True),
        ),
    ]
