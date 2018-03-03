# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('flights', '0026_auto_20141217_1307'),
    ]

    operations = [
        migrations.AlterField(
            model_name='airport',
            name='code',
            field=models.CharField(max_length=4, db_index=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='plane',
            name='model',
            field=models.CharField(default=b'Beechcraft King Air 350', max_length=64, choices=[(b'Beechcraft King Air 350', b'Beechcraft King Air 350'), (b'Beechcraft King Air B200', b'Beechcraft King Air B200')]),
            preserve_default=True,
        ),
    ]
