# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0012_auto_20141114_1728'),
    ]

    operations = [
        migrations.AlterField(
            model_name='invite',
            name='account',
            field=models.ForeignKey(related_name='account_invitations', on_delete=django.db.models.deletion.SET_NULL, blank=True, to='accounts.Account', null=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='invite',
            name='created_by',
            field=models.ForeignKey(related_name='user_invitations', on_delete=django.db.models.deletion.SET_NULL, blank=True, to=settings.AUTH_USER_MODEL, null=True),
            preserve_default=True,
        ),
    ]
