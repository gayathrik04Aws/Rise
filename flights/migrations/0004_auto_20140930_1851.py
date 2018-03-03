# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0001_initial'),
        ('accounts', '0003_auto_20140930_1851'),
        ('flights', '0003_flightfeedback'),
    ]

    operations = [
        migrations.AddField(
            model_name='flight',
            name='account_restriction',
            field=models.ManyToManyField(to='accounts.Account', null=True, blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='flight',
            name='plan_restriction',
            field=models.ManyToManyField(to='billing.Plan', null=True, blank=True),
            preserve_default=True,
        ),
    ]
