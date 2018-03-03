# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_auto_20140912_1843'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='account',
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, blank=True, to='accounts.Account', null=True),
        ),
        migrations.AlterField(
            model_name='userprofile',
            name='background_status',
            field=models.PositiveIntegerField(default=0, choices=[(0, b'Not Started'), (1, b'Processing'), (2, b'Passed'), (3, b'Failed')]),
        ),
        migrations.AlterField(
            model_name='userprofile',
            name='billing_address',
            field=models.ForeignKey(related_name=b'userprofile_billing_address_set', on_delete=django.db.models.deletion.SET_NULL, blank=True, to='accounts.Address', null=True),
        ),
        migrations.AlterField(
            model_name='userprofile',
            name='shipping_address',
            field=models.ForeignKey(related_name=b'userprofile_shipping_address_set', on_delete=django.db.models.deletion.SET_NULL, blank=True, to='accounts.Address', null=True),
        ),
    ]
