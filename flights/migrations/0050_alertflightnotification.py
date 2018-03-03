# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('flights', '0049_auto_20160317_1915'),
    ]

    operations = [
        migrations.CreateModel(
            name='AlertFlightNotification',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('hour_24', models.BooleanField(default=False)),
                ('hour_1', models.BooleanField(default=False)),
                ('createdon', models.DateTimeField(null=True, blank=True)),
                ('flight', models.ForeignKey(to='flights.Flight')),
            ],
        ),
    ]
