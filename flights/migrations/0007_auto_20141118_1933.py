# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0007_remove_charge_invoice'),
        ('flights', '0006_auto_20141118_1910'),
    ]

    operations = [
        migrations.CreateModel(
            name='FlightPlanRestriction',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('days', models.PositiveIntegerField(default=0)),
                ('flight', models.ForeignKey(to='flights.Flight')),
                ('plan', models.ForeignKey(to='billing.Plan')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.RemoveField(
            model_name='flight',
            name='plan_restriction',
        ),
    ]
