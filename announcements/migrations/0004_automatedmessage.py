# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('announcements', '0003_auto_20150217_1136'),
    ]

    operations = [
        migrations.CreateModel(
            name='AutomatedMessage',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('message_key', models.CharField(default=b'flight_dept_not_24', max_length=20, choices=[(b'flight_dept_not_24', b'Flight Departure 24 Hours '), (b'flight_dept_not_1', b'Flight Departure 1 Hour'), (b'flight_delay_not', b'Flight Delay')])),
                ('sms_text', models.CharField(max_length=160, null=True, blank=True)),
                ('email_text', models.CharField(max_length=500, null=True, blank=True)),
            ],
        ),
    ]
