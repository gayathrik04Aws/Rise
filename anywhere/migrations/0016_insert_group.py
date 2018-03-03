from __future__ import unicode_literals
from django.db import migrations
from django.contrib.auth.models import Group

def load_data(apps, schema_editor):
    group = Group(name='Anywhere Flight Creator')
    group.save()

class Migration(migrations.Migration):
    dependencies = [
        ('anywhere', '0015_auto_20160203_2106')
      ]

    operations = [
        migrations.RunPython(load_data)
    ]
