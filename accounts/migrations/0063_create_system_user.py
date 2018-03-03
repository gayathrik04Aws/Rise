from __future__ import unicode_literals
from django.db import migrations, models
from accounts.models import User,UserProfile


def load_data(apps, schema_editor):

    userprofile = UserProfile()
    userprofile.first_name='System'
    userprofile.last_name='Admin'
    userprofile.email='sysadmin@iflyrise.com'
    userprofile.save()

    user = User()
    user.first_name='System'
    user.last_name = 'Admin'
    user.email = 'sysadmin@iflyrise.com'
    user.is_staff = False
    user.is_active=True
    user.userprofile=userprofile
    user.save()


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0063_auto_20160523_1530'),
    ]

    operations = [
        migrations.RunPython(load_data)
    ]
