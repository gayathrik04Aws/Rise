# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0018_foodoptions'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='FoodOptions',
            new_name='FoodOption',
        ),
    ]
