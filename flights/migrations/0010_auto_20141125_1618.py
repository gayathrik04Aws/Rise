# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('flights', '0009_route_name'),
    ]

    operations = [
        migrations.CreateModel(
            name='FlightMessage',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('message_type', models.CharField(default=b'I', max_length=1, choices=[(b'I', b'Informational Messgae'), (b'D', b'Flight Delay Message'), (b'C', b'Cancellation Message')])),
                ('message', models.TextField(null=True, blank=True)),
                ('flight', models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, blank=True, to='flights.Flight', null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AlterField(
            model_name='flight',
            name='flight_type',
            field=models.CharField(default=b'R', max_length=1, choices=[(b'R', b'Regularly Scheduled Flight'), (b'P', b'Promotional Flight'), (b'F', b'Fun Flight')]),
            preserve_default=True,
        ),
    ]
