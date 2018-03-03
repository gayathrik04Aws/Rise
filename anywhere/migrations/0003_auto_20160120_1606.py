# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('anywhere', '0002_anywhereflightrequest'),
    ]

    operations = [
        migrations.AddField(
            model_name='anywhereflightrequest',
            name='share_with',
            field=models.CharField(default='private', max_length=64, verbose_name=b'Share Flight With', choices=[(b'public', b'Public'), (b'private', b'Private')]),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='anywhereflightrequest',
            name='status',
            field=models.CharField(default=b'new', max_length=64, verbose_name=b'Request Status', choices=[(b'new', b'New'), (b'pending', b'Pending'), (b'accepted', b'Accepted'), (b'rejected', b'Rejected')]),
        ),
        migrations.AlterField(
            model_name='anywhereflightrequest',
            name='depart_when',
            field=models.CharField(default=b'anytime', max_length=64, verbose_name=b'Departure Time of Day', choices=[(b'morning', b'Morning'), (b'afternoon', b'Afternoon'), (b'evening', b'Evening'), (b'anytime', b'Anytime')]),
        ),
        migrations.AlterField(
            model_name='anywhereflightrequest',
            name='return_when',
            field=models.CharField(default=b'anytime', max_length=64, verbose_name=b'Returning Time of Day', choices=[(b'morning', b'Morning'), (b'afternoon', b'Afternoon'), (b'evening', b'Evening'), (b'anytime', b'Anytime')]),
        ),
    ]
