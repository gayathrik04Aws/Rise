# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('anywhere', '0014_merge'),
    ]

    operations = [
        migrations.AlterField(
            model_name='anywhereroute',
            name='cost',
            field=models.DecimalField(verbose_name=b'full flight cost', max_digits=20, decimal_places=2),
        ),
    ]
