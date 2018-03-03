# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('flights', '0051_airport_map_url'),
        ('accounts', '0062_merge'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='oncallschedule',
            options={},
        ),
        migrations.RemoveField(
            model_name='oncallschedule',
            name='day',
        ),
        migrations.RemoveField(
            model_name='oncallschedule',
            name='endHour',
        ),
        migrations.RemoveField(
            model_name='oncallschedule',
            name='startHour',
        ),
        migrations.AddField(
            model_name='oncallschedule',
            name='airport',
            field=models.ForeignKey(to='flights.Airport', null=True),
        ),
        migrations.AddField(
            model_name='oncallschedule',
            name='end_date',
            field=models.DateTimeField(null=True, verbose_name=b'End Date', blank=True),
        ),
        migrations.AddField(
            model_name='oncallschedule',
            name='flights',
            field=models.ManyToManyField(to='flights.Flight', null=True),
        ),
        migrations.AddField(
            model_name='oncallschedule',
            name='start_date',
            field=models.DateTimeField(null=True, verbose_name=b'Start Date', blank=True),
        ),
    ]
