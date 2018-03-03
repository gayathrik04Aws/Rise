# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('flights', '0019_auto_20141126_1541'),
    ]

    operations = [
        migrations.AddField(
            model_name='flight',
            name='max_seats_companion',
            field=models.PositiveIntegerField(help_text=b'How many seats may be reserved for Companion users', null=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='flight',
            name='copilot',
            field=models.ForeignKey(related_name='copiloted_flights', on_delete=django.db.models.deletion.SET_NULL, blank=True, to=settings.AUTH_USER_MODEL, null=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='flight',
            name='max_seats_corporate',
            field=models.PositiveIntegerField(help_text=b'How many seats may be reserved for Corporate users', null=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='flight',
            name='pilot',
            field=models.ForeignKey(related_name='piloted_flights', on_delete=django.db.models.deletion.SET_NULL, blank=True, to=settings.AUTH_USER_MODEL, null=True),
            preserve_default=True,
        ),
    ]
