# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0004_auto_20141110_2002'),
    ]

    operations = [
        migrations.AddField(
            model_name='account',
            name='payment_method',
            field=models.CharField(default=b'C', max_length=1, choices=[(b'C', b'Credit Card'), (b'M', b'Manual')]),
            preserve_default=True,
        ),
    ]
