# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('flights', '0048_auto_20160128_1355'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='airport',
            options={'ordering': ['name']},
        ),
        migrations.AlterField(
            model_name='anywhereflightdetails',
            name='sharing',
            field=models.CharField(default=b'PUBLIC', max_length=12, choices=[(b'PUBLIC', b'Members'), (b'INVITEONLY', b'By Invitation Only'), (b'PRIVATE', b'Private / Full Flight')]),
        ),
    ]
