# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('anywhere', '0011_auto_20160127_1136'),
    ]

    operations = [
        migrations.AddField(
            model_name='anywhereflightrequest',
            name='outbound_route',
            field=models.ForeignKey(related_name='request_outbound_route', to='anywhere.AnywhereRoute', null=True),
        ),
        migrations.AddField(
            model_name='anywhereflightrequest',
            name='return_route',
            field=models.ForeignKey(related_name='request_return_route', to='anywhere.AnywhereRoute', null=True),
        ),
    ]
