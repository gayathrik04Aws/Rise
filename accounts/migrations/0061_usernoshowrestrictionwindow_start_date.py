# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import datetime
from django.utils.timezone import utc


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0061_auto_20160512_2305'),
    ]

    operations = [
        migrations.AddField(
            model_name='usernoshowrestrictionwindow',
            name='start_date',
            field=models.DateTimeField(default=datetime.datetime.now()),
            preserve_default=False,
        ),
    ]
