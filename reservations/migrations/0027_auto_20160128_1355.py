# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reservations', '0026_auto_20150928_1556'),
    ]

    operations = [
        migrations.AlterField(
            model_name='flightreservation',
            name='status',
            field=models.CharField(default=b'P', max_length=1, choices=[(b'P', b'Pending'), (b'A', b'Anywhere - Pending Confirmation'), (b'R', b'Reserved'), (b'I', b'Checked-In'), (b'C', b'Cancelled'), (b'L', b'Complete')]),
        ),
        migrations.AlterField(
            model_name='reservation',
            name='status',
            field=models.CharField(default=b'P', max_length=1, choices=[(b'P', b'Pending'), (b'A', b'Anywhere - Pending'), (b'R', b'Reserved'), (b'C', b'Cancelled'), (b'L', b'Complete')]),
        ),
    ]
