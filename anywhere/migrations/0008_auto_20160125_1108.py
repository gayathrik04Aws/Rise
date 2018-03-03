# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('anywhere', '0007_auto_20160123_0956'),
    ]

    operations = [
        migrations.AddField(
            model_name='anywhereflightset',
            name='created_by',
            field=models.ForeignKey(related_name='set_created_by', on_delete=django.db.models.deletion.SET_NULL, blank=True, to=settings.AUTH_USER_MODEL, null=True),
        ),
        migrations.AlterField(
            model_name='anywhereflightset',
            name='anywhere_request',
            field=models.ForeignKey(to='anywhere.AnywhereFlightRequest'),
        ),
        migrations.AlterField(
            model_name='anywhereflightset',
            name='flight_creator_user',
            field=models.ForeignKey(related_name='flight_creator', to=settings.AUTH_USER_MODEL),
        ),
    ]
