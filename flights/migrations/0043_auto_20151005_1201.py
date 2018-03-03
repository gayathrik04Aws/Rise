# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('flights', '0042_auto_20151001_1306'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='flightplanseatrestriction',
            unique_together=set([('flight', 'plan')]),
        ),
    ]
