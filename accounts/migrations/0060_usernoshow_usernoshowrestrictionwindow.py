# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0060_billingpaymentmethod'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserNoShow',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('flight', models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, to='flights.Flight', null=True)),
                ('user', models.ForeignKey(related_name='user_noshow', to=settings.AUTH_USER_MODEL)),
                ('userprofile', models.ForeignKey(related_name='userprofile_noshow', to='accounts.UserProfile')),
            ],
        ),
        migrations.CreateModel(
            name='UserNoShowRestrictionWindow',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('end_date', models.DateTimeField()),
                ('user', models.ForeignKey(related_name='user_noshowrestriction', to=settings.AUTH_USER_MODEL)),
                ('userprofile', models.ForeignKey(related_name='userprofile_noshowrestriction', to='accounts.UserProfile')),
            ],
        ),
    ]
