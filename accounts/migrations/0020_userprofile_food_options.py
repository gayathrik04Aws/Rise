# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0019_auto_20141119_2051'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='food_options',
            field=models.ManyToManyField(to='accounts.FoodOption', null=True, blank=True),
            preserve_default=True,
        ),
    ]
