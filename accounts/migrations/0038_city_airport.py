# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('flights', '0028_auto_20141222_1613'),
        ('accounts', '0037_usernote'),
    ]

    operations = [
        migrations.AddField(
            model_name='city',
            name='airport',
            field=models.ForeignKey(related_name='airport_city', on_delete=django.db.models.deletion.SET_NULL, blank=True, to='flights.Airport', null=True),
            preserve_default=True,
        ),
    ]
