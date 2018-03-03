# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('flights', '0045_auto_20160122_1702'),
    ]

    operations = [
        migrations.AlterField(
            model_name='anywhereflightdetails',
            name='confirmation_status',
            field=models.CharField(default=b'NOTREADY', max_length=20, choices=[(b'NOTREADY', b'Not Ready'), (b'PENDINGCONFIRMATION', b'Full - Pending Confirmation'), (b'CONFIRMED', b'Confirmed'), (b'CANCELLED', b'Cancelled')]),
        ),
    ]
