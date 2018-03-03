# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import localflavor.us.models


class Migration(migrations.Migration):

    dependencies = [
        ('reservations', '0019_passenger_checked_in'),
    ]

    operations = [
        migrations.AlterField(
            model_name='passenger',
            name='phone',
            field=localflavor.us.models.PhoneNumberField(max_length=20, null=True, blank=True),
            preserve_default=True,
        ),
    ]
