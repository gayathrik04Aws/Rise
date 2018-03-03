# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


def _wipe_existing(apps, schema_editor):
    # simply wipe existing records to accomodate the column type change
    apps.get_model('anywhere.AnywhereFlightRequest').objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('anywhere', '0006_anywhereflightset_public_key'),
    ]

    operations = [
        migrations.RunPython(_wipe_existing),
        migrations.AlterField(
            model_name='anywhereflightrequest',
            name='destination_city',
            field=models.ForeignKey(related_name='+', on_delete=django.db.models.deletion.SET_NULL, to='flights.Airport', null=True),
        ),
        migrations.AlterField(
            model_name='anywhereflightrequest',
            name='origin_city',
            field=models.ForeignKey(related_name='+', on_delete=django.db.models.deletion.SET_NULL, to='flights.Airport', null=True),
        ),
    ]
