# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0055_auto_20151027_1257'),
    ]

    operations = [
        migrations.AddField(
            model_name='account',
            name='do_not_charge',
            field=models.BooleanField(default=False),
        ),
    ]
