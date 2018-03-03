# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


def add_userprofile_to_passengers_and_waitlist(apps,schema_editor):
    users = apps.get_model("accounts","User")
    pax=apps.get_model("reservations","Passenger")
    wait_lists = apps.get_model("reservations","FlightWaitList")
    for passenger in pax.objects.all():
        user_id= passenger.user_id
        user = users.objects.filter(id=user_id).first()
        if user:
            passenger.userprofile_id = user.userprofile_id
            passenger.save()
    for wait_list in wait_lists.objects.all():
        user_id = wait_list.user_id
        user = users.objects.filter(id=user_id).first()
        if user:
            wait_list.userprofile_id = user.userprofile_id
            wait_list.save()


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0066_auto_20160601_1537'),
        ('reservations', '0034_auto_20160512_1553'),
    ]

    operations = [
        migrations.AddField(
            model_name='flightwaitlist',
            name='userprofile',
            field=models.ForeignKey(to='accounts.UserProfile', null=True),
        ),
        migrations.AddField(
            model_name='passenger',
            name='userprofile',
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, to='accounts.UserProfile', null=True),
        ),
        migrations.AlterField(
            model_name='passenger',
            name='email',
            field=models.EmailField(max_length=254, null=True),
        ),
        migrations.AlterUniqueTogether(
            name='flightwaitlist',
            unique_together=set([('userprofile', 'flight')]),
        ),
        migrations.RunPython(add_userprofile_to_passengers_and_waitlist)
    ]
