# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0020_userprofile_food_options'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userprofile',
            name='food_options',
            field=models.ManyToManyField(related_name='food_options_set', null=True, to='accounts.FoodOption', blank=True),
            preserve_default=True,
        ),
    ]
