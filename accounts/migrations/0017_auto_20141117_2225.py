# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0016_auto_20141117_2148'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='alert_billing_email',
            field=models.BooleanField(default=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='userprofile',
            name='alert_billing_sms',
            field=models.BooleanField(default=False),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='userprofile',
            name='alert_flight_email',
            field=models.BooleanField(default=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='userprofile',
            name='alert_flight_sms',
            field=models.BooleanField(default=False),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='userprofile',
            name='alert_promo_email',
            field=models.BooleanField(default=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='userprofile',
            name='alert_promo_sms',
            field=models.BooleanField(default=False),
            preserve_default=True,
        ),
    ]
