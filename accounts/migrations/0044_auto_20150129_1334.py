# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


def migrate_customer_id(apps, schema_editor):
    Customer = apps.get_model('billing', 'Customer')
    for customer in Customer.objects.all():
        account = customer.account

        account.stripe_customer_id = customer.stripe_id
        account.save(update_fields=['stripe_customer_id'])


def reverse_migrate_customer_id(apps, schema_editor):
    Account = apps.get_model('accounts', 'Account')

    Account.objects.all().update(stripe_customer_id=None)


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0043_auto_20150129_1311'),
    ]

    operations = [
        migrations.AddField(
            model_name='account',
            name='braintree_customer_id',
            field=models.CharField(max_length=64, null=True, blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='account',
            name='stripe_customer_id',
            field=models.CharField(max_length=64, null=True, blank=True),
            preserve_default=True,
        ),
        migrations.RunPython(migrate_customer_id, reverse_code=reverse_migrate_customer_id),
    ]
