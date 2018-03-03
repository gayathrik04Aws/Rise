# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models

def create_anywhereplus_plan(apps, schema_editor):
    # create a new billing.Plan for Anywhere Basic
    plans = apps.get_model("billing", "Plan")
    plan = plans()
    plan.name = "Anywhere Plus"
    plan.amount=79
    plan.interval='month'
    plan.interval_count=1
    plan.companion_passes=0
    plan.active=1
    plan.pass_count=0
    plan.description='RISE Anywhere Plus Plan - can request new Anywhere flights'
    plan.anywhere_only=1
    plan.save()

class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0030_auto_20160118_1355'),
    ]

    operations = [
         migrations.RunPython(create_anywhereplus_plan)
    ]
