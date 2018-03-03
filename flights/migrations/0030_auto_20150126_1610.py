# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('flights', '0029_auto_20150105_1237'),
    ]

    operations = [
        migrations.AddField(
            model_name='flight',
            name='founder',
            field=models.BooleanField(default=False, help_text=b'Restrict flight to Founder accounts'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='flight',
            name='vip',
            field=models.BooleanField(default=False, help_text=b'Restrict flight to VIP accounts'),
            preserve_default=True,
        ),
    ]
