# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0015_auto_20150129_1513'),
    ]

    operations = [
        migrations.RenameField(
            model_name='card',
            old_name='stripe_id',
            new_name='token',
        ),
        migrations.RemoveField(
            model_name='card',
            name='fingerprint',
        ),
    ]
