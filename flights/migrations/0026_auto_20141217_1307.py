# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('flights', '0025_auto_20141217_0912'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='flightmessage',
            name='message_type',
        ),
        migrations.RemoveField(
            model_name='flightmessage',
            name='title',
        ),
        migrations.AddField(
            model_name='flightmessage',
            name='created_by',
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, blank=True, to=settings.AUTH_USER_MODEL, null=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='flightmessage',
            name='message',
            field=models.TextField(max_length=160),
            preserve_default=True,
        ),
    ]
