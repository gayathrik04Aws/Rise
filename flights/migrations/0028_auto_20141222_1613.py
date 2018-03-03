# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('flights', '0027_auto_20141222_1545'),
    ]

    operations = [
        migrations.AlterField(
            model_name='flight',
            name='route_time',
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, blank=True, to='flights.RouteTime', null=True),
            preserve_default=True,
        ),
    ]
