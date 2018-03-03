# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('flights', '0051_airport_map_url'),
    ]

    operations = [
        migrations.AddField(
            model_name='route',
            name='plane',
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, to='flights.Plane', null=True),
        ),
        migrations.AddField(
            model_name='routetime',
            name='plane',
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, to='flights.Plane', null=True),
        ),
    ]
