# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


def get_primary_member(apps, schema_editor):
    # looking up current rows and setting their primary user if needed
    Account = apps.get_model("accounts", "Account")
    for account in Account.objects.all():
        if account.get_primary_user:
            account.primary_user = account.get_primary_user
            account.save()
        else:
            account.delete()


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0039_account_onboarding_fee_paid'),
    ]

    operations = [
        migrations.AddField(
            model_name='account',
            name='primary_user',
            field=models.ForeignKey(related_name='primary_members', default=2, to=settings.AUTH_USER_MODEL),
            preserve_default=False,
        ),
        migrations.RunPython(
            get_primary_member,
        ),
    ]
