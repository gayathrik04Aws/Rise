# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0066_auto_20160601_1537'),
    ]

    operations = [
        migrations.AlterField(
            model_name='usernoshow',
            name='user',
            field=models.ForeignKey(related_name='user_noshow', blank=True, to=settings.AUTH_USER_MODEL, null=True),
        ),
        migrations.AlterField(
            model_name='usernoshowrestrictionwindow',
            name='user',
            field=models.ForeignKey(related_name='user_noshowrestriction', blank=True, to=settings.AUTH_USER_MODEL, null=True),
        ),
    ]
