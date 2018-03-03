# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0018_charge_payment_method'),
    ]

    operations = [
        migrations.RenameField(
            model_name='chargerefund',
            old_name='stripe_id',
            new_name='vault_id',
        ),
    ]
