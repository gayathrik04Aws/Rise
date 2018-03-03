# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings


def add_userprofile_to_note(apps,schema_editor):
    users = apps.get_model("accounts","User")
    notes=apps.get_model("accounts","UserNote")
    for note in notes.objects.all():
        user_id= note.user_id
        user = users.objects.filter(id=user_id).first()
        if user:
            note.userprofile_id = user.userprofile_id
            note.save()

class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0065_account_primary_profile'),
    ]

    operations = [
        migrations.AddField(
            model_name='usernote',
            name='userprofile',
            field=models.ForeignKey(related_name='note_userprofile', blank=True, to='accounts.UserProfile', null=True),
        ),
        migrations.AlterField(
            model_name='usernote',
            name='user',
            field=models.ForeignKey(related_name='note_user', blank=True, to=settings.AUTH_USER_MODEL, null=True),
        ),
        migrations.RunPython(add_userprofile_to_note)
    ]
