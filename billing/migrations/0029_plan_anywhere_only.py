# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0028_subscription_created_by'),
    ]

    operations = [
        migrations.AddField(
            model_name='plan',
            name='anywhere_only',
            field=models.BooleanField(default=False),
        ),
    ]
