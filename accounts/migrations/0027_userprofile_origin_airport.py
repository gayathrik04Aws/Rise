# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('flights', '0023_auto_20141203_1704'),
        ('accounts', '0026_remove_userprofile_food_preferences'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='origin_airport',
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, blank=True, to='flights.Airport', null=True),
            preserve_default=True,
        ),
    ]
