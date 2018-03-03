# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('reservations', '0002_auto_20141121_1803'),
    ]

    operations = [
        migrations.AddField(
            model_name='reservation',
            name='expires',
            field=models.DateTimeField(null=True, blank=True),
            preserve_default=True,
        ),
    ]
