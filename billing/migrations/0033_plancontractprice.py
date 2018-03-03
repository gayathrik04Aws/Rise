# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0032_plan_has_onboarding'),
    ]

    operations = [
        migrations.CreateModel(
            name='PlanContractPrice',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('contract_length', models.PositiveIntegerField(choices=[(3, b'3 Month'), (6, b'6 Month'), (12, b'12 Month')])),
                ('amount', models.DecimalField(max_digits=10, decimal_places=2)),
                ('selectable', models.BooleanField(default=True)),
                ('plan', models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, to='billing.Plan', null=True)),
            ],
        ),
    ]
