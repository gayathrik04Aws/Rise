# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0028_auto_20141215_1432'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userprofile',
            name='weight',
            field=models.PositiveIntegerField(default=0, choices=[(99, b'< 100'), (100, b'100 - 124'), (125, b'125 - 149'), (150, b'150 - 174'), (175, b'175 - 199'), (200, b'200 - 224'), (225, b'225 - 249'), (250, b'250 - 274'), (275, b'275 - 299'), (300, b'300 - 324'), (325, b'325 - 349'), (350, b'350+')]),
            preserve_default=True,
        ),
    ]
