# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0061_usernoshowrestrictionwindow_start_date'),
        ('reservations', '0033_auto_20160510_1756'),
    ]

    operations = [
        migrations.AddField(
            model_name='flightpassengeraudittrail',
            name='user_profile',
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, blank=True, to='accounts.UserProfile', null=True),
        ),
        migrations.AlterField(
            model_name='flightpassengeraudittrail',
            name='update_type',
            field=models.PositiveIntegerField(default=0, choices=[(0, b'Update Background Check Status'), (1, b'Passenger removed from flight')]),
        ),
    ]
