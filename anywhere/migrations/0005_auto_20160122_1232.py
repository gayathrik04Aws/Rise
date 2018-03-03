# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('anywhere', '0004_anywhereflightset'),
    ]

    operations = [
        migrations.AlterField(
            model_name='anywhereflightset',
            name='confirmation_status',
            field=models.CharField(default=b'NOTFULL', max_length=20, choices=[(b'NOTFULL', b'Not Ready'), (b'PENDINGCONFIRMATION', b'Full - Pending Confirmation'), (b'CONFIRMED', b'Confirmed'), (b'CANCELLED', b'Cancelled')]),
        ),
        migrations.AlterField(
            model_name='anywhereflightset',
            name='sharing',
            field=models.CharField(default=(b'PUBLIC',), max_length=12, choices=[((b'PUBLIC',), b'Public'), ((b'INVITEONLY',), b'By Invitation Only'), (b'PRIVATE', b'Private / Full Flight')]),
        ),
    ]
