# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.db.models.deletion
import datetime
from django.utils.timezone import utc


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0020_auto_20150203_1558'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='subscription',
            name='braintree_id',
        ),
        migrations.RemoveField(
            model_name='subscription',
            name='current_period_end',
        ),
        migrations.RemoveField(
            model_name='subscription',
            name='current_period_start',
        ),
        migrations.RemoveField(
            model_name='subscription',
            name='ended_at',
        ),
        migrations.RemoveField(
            model_name='subscription',
            name='plan',
        ),
        migrations.RemoveField(
            model_name='subscription',
            name='stripe_id',
        ),
        migrations.AddField(
            model_name='charge',
            name='subscription',
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, blank=True, to='billing.Subscription', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='subscription',
            name='amount',
            field=models.DecimalField(default=0, max_digits=10, decimal_places=2),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='subscription',
            name='created',
            field=models.DateTimeField(default=datetime.datetime(2015, 2, 6, 16, 23, 33, 562893, tzinfo=utc), auto_now_add=True),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='subscription',
            name='description',
            field=models.CharField(max_length=256, null=True, blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='subscription',
            name='period_end',
            field=models.DateField(null=True, blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='subscription',
            name='period_start',
            field=models.DateField(null=True, blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='subscription',
            name='status',
            field=models.CharField(default=b'active', max_length=16, choices=[(b'active', b'Acitve'), (b'past_due', b'Past Due'), (b'canceled', b'Cancelled')]),
            preserve_default=True,
        ),
    ]
