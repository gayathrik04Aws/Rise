# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('flights', '0022_auto_20141203_1649'),
    ]

    operations = [
        migrations.AlterField(
            model_name='flightplanrestriction',
            name='flight',
            field=models.ForeignKey(to='flights.Flight'),
            preserve_default=True,
        ),
    ]
