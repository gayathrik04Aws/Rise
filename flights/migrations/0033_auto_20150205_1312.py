# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('flights', '0032_remove_flightmessage_message_details'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='flightmessage',
            options={'ordering': ('-created',)},
        ),
    ]
