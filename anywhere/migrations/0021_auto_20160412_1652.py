# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('anywhere', '0020_auto_20160317_1924'),
    ]

    operations = [
        migrations.AlterField(
            model_name='anywhereflightset',
            name='confirmation_status',
            field=models.CharField(default=b'NOTFULL', max_length=20, choices=[(b'NOTFULL', b'Not Ready'), (b'PENDINGCONFIRMATION', b'Full - Pending Confirmation'), (b'CONFIRMED', b'Confirmed'), (b'CANCELLED', b'Cancelled'), (b'PARTLYCANCELLED', b'Leg 1 Complete / Leg 2 Cancelled')]),
        ),
    ]
