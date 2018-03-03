# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('flights', '0043_auto_20151005_1201'),
    ]

    operations = [
        migrations.CreateModel(
            name='AnywhereRoute',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=128)),
                ('duration', models.PositiveIntegerField()),
                ('cost', models.DecimalField(verbose_name=b'Cost Per Seat', max_digits=20, decimal_places=2)),
                ('destination', models.ForeignKey(related_name='destination_anywhereroutes', to='flights.Airport')),
                ('origin', models.ForeignKey(related_name='origin_anywhereroutes', to='flights.Airport')),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
