# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models

def update_plans_hasonboarding(apps, schema_editor):
    plans = apps.get_model("billing", "Plan")
    # AnywhereOnly plans have no onboarding
    for plan in plans.objects.filter(anywhere_only=True).all():
        plan.has_onboarding=False
        plan.save()
    # Trial has no onboarding
    trial = plans.objects.filter(name='Trial').first()
    trial.has_onboarding=False
    trial.save()

class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0031_auto_20160304_1127'),
    ]

    operations = [
        migrations.AddField(
            model_name='plan',
            name='has_onboarding',
            field=models.BooleanField(default=True),
        ),
        migrations.RunPython(update_plans_hasonboarding)
    ]
