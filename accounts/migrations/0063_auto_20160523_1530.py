# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


def add_acct_to_up(apps,schema_editor):
    users=apps.get_model("accounts","User")
    ups=apps.get_model("accounts","UserProfile")
    for user in users.objects.all():
        up = ups.objects.filter(id=user.userprofile_id).first()
        up.account_id=user.account_id
        up.save()


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0062_auto_20160523_1440'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='userprofile',
            name='user',
        ),
        migrations.AddField(
            model_name='userprofile',
            name='account',
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, blank=True, to='accounts.Account', null=True),
        ),
        migrations.RunPython(add_acct_to_up)
    ]
