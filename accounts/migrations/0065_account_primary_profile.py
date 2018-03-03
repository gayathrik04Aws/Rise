# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models

def add_primary_profile_to_account(apps,schema_editor):
    users = apps.get_model("accounts","User")
    accts=apps.get_model("accounts","Account")
    for acct in accts.objects.all():
        user_id= acct.primary_user_id
        user = users.objects.filter(id=user_id).first()
        if user:
            acct.primary_profile_id = user.userprofile_id
            acct.save()

class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0064_auto_20160523_1620'),
    ]

    operations = [
        migrations.AddField(
            model_name='account',
            name='primary_profile',
            field=models.ForeignKey(related_name='primary_profiles', default=None, to='accounts.UserProfile', null=True),
        ),
        migrations.RunPython(add_primary_profile_to_account)
    ]
