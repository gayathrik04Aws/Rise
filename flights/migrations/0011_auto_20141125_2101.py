# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('flights', '0010_auto_20141125_1618'),
    ]

    operations = [
        migrations.AddField(
            model_name='flight',
            name='pilot',
            field=models.ForeignKey(related_name='piloted_flights', on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL, null=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='flightmessage',
            name='message_type',
            field=models.CharField(default=b'I', max_length=1, choices=[(b'I', b'Information'), (b'D', b'Delay'), (b'C', b'Cancellation')]),
            preserve_default=True,
        ),
    ]
