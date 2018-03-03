# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0047_auto_20150220_0957'),
    ]

    operations = [
        migrations.AlterField(
            model_name='account',
            name='available_companion_passes',
            field=models.IntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='account',
            name='available_passes',
            field=models.IntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='account',
            name='preferred_cities',
            field=models.ManyToManyField(to='accounts.City', blank=True),
        ),
        migrations.AlterField(
            model_name='account',
            name='status',
            field=models.CharField(default=b'P', max_length=1, choices=[(b'P', b'Pending'), (b'A', b'Active'), (b'S', b'Suspended'), (b'V', b'Pending ACH Verification')]),
        ),
        migrations.AlterField(
            model_name='invite',
            name='email',
            field=models.EmailField(max_length=254, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='user',
            name='email',
            field=models.EmailField(unique=True, max_length=254),
        ),
        migrations.AlterField(
            model_name='user',
            name='groups',
            field=models.ManyToManyField(related_query_name='user', related_name='user_set', to='auth.Group', blank=True, help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.', verbose_name='groups'),
        ),
        migrations.AlterField(
            model_name='user',
            name='last_login',
            field=models.DateTimeField(null=True, verbose_name='last login', blank=True),
        ),
        migrations.AlterField(
            model_name='userprofile',
            name='food_options',
            field=models.ManyToManyField(to='accounts.FoodOption', blank=True),
        ),
        migrations.AlterField(
            model_name='waitlist',
            name='email',
            field=models.EmailField(max_length=254),
        ),
    ]
