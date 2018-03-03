# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0056_account_do_not_charge'),
    ]

    operations = [
        migrations.CreateModel(
            name='OncallSchedule',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('day', models.CharField(max_length=10, choices=[(b'MONDAY', b'MONDAY'), (b'TUESDAY', b'TUESDAY'), (b'WEDNESDAY', b'WEDNESDAY'), (b'THURSDAY', b'THURSDAY'), (b'FRIDAY', b'FRIDAY'), (b'SATURDAY', b'SATURDAY'), (b'SUNDAY', b'SUNDAY')])),
                ('startHour', models.IntegerField(choices=[(0, b'0:00'), (1, b'1:00'), (2, b'2:00'), (3, b'3:00'), (4, b'4:00'), (5, b'5:00'), (6, b'6:00'), (7, b'7:00'), (8, b'8:00'), (9, b'9:00'), (10, b'10:00'), (11, b'11:00'), (12, b'12:00'), (13, b'13:00'), (14, b'14:00'), (15, b'15:00'), (16, b'16:00'), (17, b'17:00'), (18, b'18:00'), (19, b'19:00'), (20, b'20:00'), (21, b'21:00'), (22, b'22:00'), (23, b'23:00')])),
                ('endHour', models.IntegerField(choices=[(0, b'0:00'), (1, b'1:00'), (2, b'2:00'), (3, b'3:00'), (4, b'4:00'), (5, b'5:00'), (6, b'6:00'), (7, b'7:00'), (8, b'8:00'), (9, b'9:00'), (10, b'10:00'), (11, b'11:00'), (12, b'12:00'), (13, b'13:00'), (14, b'14:00'), (15, b'15:00'), (16, b'16:00'), (17, b'17:00'), (18, b'18:00'), (19, b'19:00'), (20, b'20:00'), (21, b'21:00'), (22, b'22:00'), (23, b'23:00')])),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-day'],
            },
        ),
    ]
