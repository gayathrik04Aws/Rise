# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0022_auto_20141119_2200'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userprofile',
            name='weight',
            field=models.PositiveIntegerField(default=200, choices=[(100, b'0 - 100'), (200, b'101 - 200'), (300, b'201 - 300'), (400, b'301 - 400'), (500, b'401 - 500'), (600, b'501 - 600')]),
            preserve_default=True,
        ),
    ]
