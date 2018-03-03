# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('flights', '0044_auto_20160121_1226'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('anywhere', '0003_auto_20160120_1606'),
    ]

    operations = [
        migrations.CreateModel(
            name='AnywhereFlightSet',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('full_flight_cost', models.DecimalField(default=0, max_digits=10, decimal_places=2)),
                ('per_seat_cost', models.DecimalField(default=0, max_digits=10, decimal_places=2)),
                ('confirmation_status', models.CharField(default=b'N', max_length=1, choices=[(b'N', b'Not Ready'), (b'P', b'Full - Pending Confirmation'), (b'C', b'Confirmed'), (b'X', b'Cancelled')])),
                ('sharing', models.CharField(default=(b'PUBLIC',), max_length=12, choices=[((b'PUBLIC',), b'Public'), ((b'INVITEONLY',), b'By Invitation Only'), ((b'INVITEONLY',), b'Private / Full Flight')])),
                ('anywhere_request', models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, blank=True, to='anywhere.AnywhereFlightRequest', null=True)),
                ('flight_creator_user', models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, blank=True, to=settings.AUTH_USER_MODEL, null=True)),
                ('leg1', models.ForeignKey(related_name='OUTBOUND', to='flights.Flight')),
                ('leg2', models.ForeignKey(related_name='RETURN', on_delete=django.db.models.deletion.SET_NULL, to='flights.Flight', null=True)),
            ],
        ),
    ]
