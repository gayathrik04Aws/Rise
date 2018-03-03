# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import datetime

from django.db import migrations, models
from django.db.models import Q

def set_plan_requires_contracts(apps, schema_editor):
    plans = apps.get_model("billing", "Plan")

    regularplans = ['Express', 'Executive', 'Chairman']
    for plan in plans.objects.filter(anywhere_only=False).all():
        if next((x for x in regularplans if x == plan.name), None):
            plan.requires_contract = True
            plan.save()


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0034_auto_20160415_1137'),
    ]

    operations = [
        migrations.AddField(
            model_name='plan',
            name='requires_contract',
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(set_plan_requires_contracts)
    ]
