# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


def init_food_options(apps, schema_editor):
    # We can't import the Person model directly as it may be a newer
    # version than this migration expects. We use the historical version.
    FoodOption = apps.get_model('accounts', 'FoodOption')

    # delete any existing food options
    FoodOption.objects.all().delete()

    FoodOption.objects.create(title='Water')
    FoodOption.objects.create(title='Coffee')
    FoodOption.objects.create(title='Juice')
    FoodOption.objects.create(title='Soda')
    FoodOption.objects.create(title='Vodka')
    FoodOption.objects.create(title='Rum')
    FoodOption.objects.create(title='Gin')
    FoodOption.objects.create(title='Wine')


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0029_auto_20141218_1316'),
    ]

    operations = [
        migrations.RunPython(init_food_options),
    ]
