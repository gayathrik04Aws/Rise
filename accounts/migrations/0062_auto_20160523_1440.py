# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


def ensure_users_have_user_profiles(apps,schema_editor):
    users=apps.get_model("accounts","User")
    ups=apps.get_model("accounts","UserProfile")
    for user in users.objects.filter(user_profile__isnull=True).all():
        up=ups()
        up.user_id=user.id
        up.first_name = user.first_name
        up.last_name = user.last_name
        up.email = user.email
        up.user=user
        up.background=0
        if up.user_id and up.user_id > 0:
            up.save()


def add_userprofile_to_user_and_setnames(apps,schema_editor):
    users=apps.get_model("accounts","User")
    ups=apps.get_model("accounts","UserProfile")
    for up in ups.objects.all():
        user=users.objects.filter(id=up.user_id).first()
        if user:
            user.userprofile=up
            up.first_name=user.first_name
            up.last_name=user.last_name
            up.email=user.email
            user.save()
            up.save()

class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0061_auto_20160520_1627'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='userprofile',
            field=models.OneToOneField(related_name='user', null=True, blank=True, to='accounts.UserProfile'),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='email',
            field=models.EmailField(max_length=254, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='first_name',
            field=models.CharField(default='tbd', max_length=30),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='userprofile',
            name='last_name',
            field=models.CharField(default='tbd', max_length=30),
            preserve_default=False,
        ),
        migrations.RunPython(ensure_users_have_user_profiles),
        migrations.RunPython(add_userprofile_to_user_and_setnames)
    ]
