# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('flights', '0017_flight_copilot'),
    ]

    operations = [
        migrations.AddField(
            model_name='flight',
            name='seats_corporate',
            field=models.PositiveIntegerField(help_text=b'How many seats reserved for Corporate users', null=True),
            preserve_default=True,
        ),
    ]
