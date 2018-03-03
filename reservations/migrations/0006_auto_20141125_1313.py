# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('reservations', '0005_auto_20141124_1626'),
    ]

    operations = [
        migrations.AddField(
            model_name='flightreservation',
            name='buy_companion_pass_count',
            field=models.PositiveIntegerField(default=0),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='flightreservation',
            name='buy_pass_count',
            field=models.PositiveIntegerField(default=0),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='flightreservation',
            name='companion_pass_count',
            field=models.PositiveIntegerField(default=0),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='flightreservation',
            name='complimentary_companion_pass_count',
            field=models.PositiveIntegerField(default=0),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='flightreservation',
            name='complimentary_pass_count',
            field=models.PositiveIntegerField(default=0),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='flightreservation',
            name='pass_count',
            field=models.PositiveIntegerField(default=0),
            preserve_default=True,
        ),
    ]
