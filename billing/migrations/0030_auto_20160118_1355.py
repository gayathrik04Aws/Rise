# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


def create_anywhere_plan(apps, schema_editor):
    # create a new billing.Plan for Anywhere Basic
    plans = apps.get_model("billing", "Plan")
    plan = plans()
    plan.name = "Anywhere Basic"
    plan.amount=0
    plan.interval='month'
    plan.interval_count=1
    plan.companion_passes=0
    plan.active=1
    plan.pass_count=0
    plan.description='RISE Anywhere Basic Plan - can book seat on Anywhere flights, cannot create flights'
    plan.anywhere_only=1
    plan.save()

class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0029_plan_anywhere_only'),
    ]

    operations = [
        migrations.RunPython(create_anywhere_plan)
    ]
