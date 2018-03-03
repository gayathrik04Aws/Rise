# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('anywhere', '0005_auto_20160122_1232'),
    ]

    operations = [
        migrations.AddField(
            model_name='anywhereflightset',
            name='public_key',
            field=models.UUIDField(default=uuid.uuid4, editable=False),
        ),
    ]
