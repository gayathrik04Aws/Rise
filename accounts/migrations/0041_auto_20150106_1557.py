# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0040_account_primary_user'),
    ]

    operations = [
        migrations.AlterField(
            model_name='account',
            name='primary_user',
            field=models.ForeignKey(related_name='primary_members', default=None, to=settings.AUTH_USER_MODEL, null=True),
            preserve_default=True,
        ),
    ]
