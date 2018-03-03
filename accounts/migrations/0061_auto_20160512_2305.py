# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0060_usernoshow_usernoshowrestrictionwindow'),
    ]

    operations = [
        migrations.AlterField(
            model_name='billingpaymentmethod',
            name='nickname',
            field=models.CharField(max_length=20, null=True),
        ),
    ]
