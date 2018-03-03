# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('anywhere', '0011_auto_20160127_1136'),
    ]

    operations = [
        migrations.AlterField(
            model_name='anywhereflightrequest',
            name='return_date',
            field=models.DateField(null=True, verbose_name=b'Returning Date', blank=True),
        ),
        migrations.AlterField(
            model_name='anywhereflightrequest',
            name='return_when',
            field=models.CharField(default=b'anytime', choices=[(b'morning', b'Morning'), (b'afternoon', b'Afternoon'), (b'evening', b'Evening'), (b'anytime', b'Anytime')], max_length=64, blank=True, null=True, verbose_name=b'Returning Time of Day'),
        ),
    ]
