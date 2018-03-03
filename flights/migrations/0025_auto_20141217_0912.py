# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('flights', '0024_auto_20141210_1006'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='routetime',
            options={'ordering': ('departure',)},
        ),
    ]
