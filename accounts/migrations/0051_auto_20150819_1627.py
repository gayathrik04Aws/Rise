# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0050_auto_20150819_1623'),
    ]

    operations = [
        migrations.AlterField(
            model_name='account',
            name='complimentary_companion_passes',
            field=models.IntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='account',
            name='complimentary_passes',
            field=models.IntegerField(default=0),
        ),
    ]
