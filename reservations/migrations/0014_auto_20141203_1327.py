# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('reservations', '0013_flightwaitlist_passenger_count'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='flightwaitlist',
            unique_together=set([('user', 'flight')]),
        ),
    ]
