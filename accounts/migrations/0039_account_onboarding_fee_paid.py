# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


def default_paid_fee(apps, schema_editor):
    # looking up current rows and setting their primary user if needed
    Account = apps.get_model('accounts', 'Account')
    Account.objects.all().update(onboarding_fee_paid=True)


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0038_city_airport'),
    ]

    operations = [
        migrations.AddField(
            model_name='account',
            name='onboarding_fee_paid',
            field=models.BooleanField(default=False),
            preserve_default=True,
        ),
        migrations.RunPython(default_paid_fee),
    ]
