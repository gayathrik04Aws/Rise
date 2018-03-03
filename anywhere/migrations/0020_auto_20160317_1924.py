# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('anywhere', '0019_auto_20160317_1915'),
    ]

    operations = [
        migrations.AlterField(
            model_name='anywhereflightrequest',
            name='depart_when',
            field=models.CharField(default=b'anytime', max_length=64, verbose_name=b'Depart Time', choices=[(b'morning', b'Morning'), (b'afternoon', b'Afternoon'), (b'evening', b'Evening'), (b'anytime', b'Anytime')]),
        ),
    ]
