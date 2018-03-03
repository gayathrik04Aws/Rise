# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0057_oncallschedule'),
    ]

    operations = [
        migrations.AlterField(
            model_name='oncallschedule',
            name='endHour',
            field=models.IntegerField(choices=[(0, b'12:00 AM'), (1, b'1:00 AM'), (2, b'2:00 AM'), (3, b'3:00 AM'), (4, b'4:00 AM'), (5, b'5:00 AM'), (6, b'6:00 AM'), (7, b'7:00 AM'), (8, b'8:00 AM'), (9, b'9:00 AM'), (10, b'10:00 AM'), (11, b'11:00 AM'), (12, b'12:00 PM'), (13, b'1:00 PM'), (14, b'2:00 PM'), (15, b'3:00 PM'), (16, b'4:00 PM'), (17, b'5:00 PM'), (18, b'6:00 PM'), (19, b'7:00 PM'), (20, b'8:00 PM'), (21, b'9:00 PM'), (22, b'10:00 PM'), (23, b'11:00 PM')]),
        ),
        migrations.AlterField(
            model_name='oncallschedule',
            name='startHour',
            field=models.IntegerField(choices=[(0, b'12:00 AM'), (1, b'1:00 AM'), (2, b'2:00 AM'), (3, b'3:00 AM'), (4, b'4:00 AM'), (5, b'5:00 AM'), (6, b'6:00 AM'), (7, b'7:00 AM'), (8, b'8:00 AM'), (9, b'9:00 AM'), (10, b'10:00 AM'), (11, b'11:00 AM'), (12, b'12:00 PM'), (13, b'1:00 PM'), (14, b'2:00 PM'), (15, b'3:00 PM'), (16, b'4:00 PM'), (17, b'5:00 PM'), (18, b'6:00 PM'), (19, b'7:00 PM'), (20, b'8:00 PM'), (21, b'9:00 PM'), (22, b'10:00 PM'), (23, b'11:00 PM')]),
        ),
    ]
