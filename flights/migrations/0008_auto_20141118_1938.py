# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0007_remove_charge_invoice'),
        ('accounts', '0017_auto_20141117_2225'),
        ('flights', '0007_auto_20141118_1933'),
    ]

    operations = [
        migrations.CreateModel(
            name='RouteTimePlanRestriction',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('days', models.PositiveIntegerField(default=0)),
                ('plan', models.ForeignKey(to='billing.Plan')),
                ('route_time', models.ForeignKey(to='flights.RouteTime')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='routetime',
            name='account_restriction',
            field=models.ManyToManyField(to='accounts.Account', null=True, blank=True),
            preserve_default=True,
        ),
    ]
