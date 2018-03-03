# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('flights', '0018_flight_seats_corporate'),
    ]

    operations = [
        migrations.RenameField(
            model_name='flight',
            old_name='seats_corporate',
            new_name='max_seats_corporate',
        ),
    ]
