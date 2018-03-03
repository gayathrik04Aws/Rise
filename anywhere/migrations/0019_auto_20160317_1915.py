# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('anywhere', '0018_anywhereflightset_seats_required'),
    ]

    operations = [
        migrations.AlterField(
            model_name='anywhereflightrequest',
            name='depart_date',
            field=models.DateField(null=True, verbose_name=b'Departure Date', blank=True),
        ),
        migrations.AlterField(
            model_name='anywhereflightrequest',
            name='depart_when',
            field=models.CharField(default=b'anytime', max_length=64, verbose_name=b'Departure Time', choices=[(b'morning', b'Morning'), (b'afternoon', b'Afternoon'), (b'evening', b'Evening'), (b'anytime', b'Anytime')]),
        ),
        migrations.AlterField(
            model_name='anywhereflightrequest',
            name='return_when',
            field=models.CharField(default=b'anytime', choices=[(b'morning', b'Morning'), (b'afternoon', b'Afternoon'), (b'evening', b'Evening'), (b'anytime', b'Anytime')], max_length=64, blank=True, null=True, verbose_name=b'Return Time'),
        ),
        migrations.AlterField(
            model_name='anywhereflightrequest',
            name='sharing',
            field=models.CharField(default=b'PUBLIC', max_length=64, verbose_name=b'Share Flight With', choices=[(b'PUBLIC', b'Members'), (b'INVITEONLY', b'By Invitation Only'), (b'PRIVATE', b'Private / Full Flight')]),
        ),
        migrations.AlterField(
            model_name='anywhereflightset',
            name='confirmation_status',
            field=models.CharField(default=b'NOTFULL', max_length=20, choices=[(b'NOTFULL', b'Not Ready'), (b'PENDINGCONFIRMATION', b'Full - Pending Confirmation'), (b'CONFIRMED', b'Confirmed'), ((b'CANCELLED',), b'Cancelled'), (b'PARTLYCANCELLED', b'Leg 1 Complete / Leg 2 Cancelled')]),
        ),
        migrations.AlterField(
            model_name='anywhereflightset',
            name='sharing',
            field=models.CharField(default=b'PUBLIC', max_length=12, choices=[(b'PUBLIC', b'Members'), (b'INVITEONLY', b'By Invitation Only'), (b'PRIVATE', b'Private / Full Flight')]),
        ),
    ]
