# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('accounts', '0012_auto_20141113_1939'),
        ('billing', '0003_auto_20141117_1541'),
    ]

    operations = [
        migrations.AddField(
            model_name='charge',
            name='account',
            field=models.OneToOneField(null=True, blank=True, to='accounts.Account'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='charge',
            name='created_by',
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, blank=True, to=settings.AUTH_USER_MODEL, null=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='charge',
            name='customer',
            field=models.ForeignKey(related_name='charges', blank=True, to='billing.Customer', null=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='charge',
            name='stripe_id',
            field=models.CharField(max_length=64, null=True, blank=True),
            preserve_default=True,
        ),
    ]
