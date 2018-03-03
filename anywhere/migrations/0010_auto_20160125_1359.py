# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('anywhere', '0009_merge'),
    ]

    operations = [
        migrations.AlterField(
            model_name='anywhereflightrequest',
            name='sharing',
            field=models.CharField(default=b'PUBLIC', max_length=64, verbose_name=b'Share Flight With', choices=[(b'PUBLIC', b'Public'), (b'INVITEONLY', b'By Invitation Only'), (b'INVITEONLY', b'Private / Full Flight')]),
        ),
        migrations.AlterField(
            model_name='anywhereflightset',
            name='sharing',
            field=models.CharField(default=b'PUBLIC', max_length=12, choices=[(b'PUBLIC', b'Public'), (b'INVITEONLY', b'By Invitation Only'), (b'INVITEONLY', b'Private / Full Flight')]),
        ),
    ]
