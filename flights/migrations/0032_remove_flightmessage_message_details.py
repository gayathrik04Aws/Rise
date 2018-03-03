# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('flights', '0031_flightmessage_message_details'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='flightmessage',
            name='message_details',
        ),
    ]
