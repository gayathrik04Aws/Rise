# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('anywhere', '0003_auto_20160120_1606'),
        ('flights', '0043_auto_20151005_1201'),
    ]

    operations = [
        migrations.CreateModel(
            name='AnywhereFlightDetails',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('confirmation_status', models.CharField(default=b'N', max_length=1, choices=[(b'N', b'Not Ready'), (b'P', b'Full - Pending Confirmation'), (b'C', b'Confirmed'), (b'X', b'Cancelled')])),
                ('full_flight_cost', models.DecimalField(default=0, max_digits=10, decimal_places=2)),
                ('per_seat_cost', models.DecimalField(default=0, max_digits=10, decimal_places=2)),
                ('sharing', models.CharField(default=(b'PUBLIC',), max_length=12, choices=[((b'PUBLIC',), b'Public'), ((b'INVITEONLY',), b'By Invitation Only'), ((b'INVITEONLY',), b'Private / Full Flight')])),
                ('anywhere_request', models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, blank=True, to='anywhere.AnywhereFlightRequest', null=True)),
                ('flight_creator_user', models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, blank=True, to=settings.AUTH_USER_MODEL, null=True)),
            ],
        ),
        migrations.AddField(
            model_name='flight',
            name='anywhere_details',
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, to='flights.AnywhereFlightDetails', null=True),
        ),
    ]
