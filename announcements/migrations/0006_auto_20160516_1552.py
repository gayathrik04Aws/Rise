# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from announcements.models import AutomatedMessage

def load_data(apps, schema_editor):
    #create new messages for no-shows, and update the flight delay to use new message box text field.
    noshow_admin = AutomatedMessage()
    noshow_admin.message_key = AutomatedMessage.NO_SHOW_RESTRICTION_ADMIN
    noshow_admin.sms_text = "Not Used"
    noshow_admin.email_text = "Not Used"
    noshow_admin.message_box_text = "This person is currently suspended due to three missed flights within a 90-day period. This account will be fully reinstated on [[end_date]]."
    noshow_admin.substitution_info = "[[end_date]]"
    noshow_admin.save()

    noshow_member = AutomatedMessage()
    noshow_member.message_key = AutomatedMessage.NO_SHOW_RESTRICTION_MEMBER
    noshow_member.sms_text = "Not Used"
    noshow_member.email_text = "Not Used"
    noshow_member.message_box_text = "We’re sorry but your account is currently suspended due to three missed flights within a 90-day period. Information about our No Show policy can be found [[FAQ_link]]. Your account will be fully reinstated on [[end_date]]."
    noshow_member.substitution_info = "[[end_date]],[[FAQ_link]]"
    noshow_member.save()

    delay = AutomatedMessage.objects.filter(message_key=AutomatedMessage.FLIGHT_DELAY_NOTIFICATION).first()
    if delay:
        delay.message_box_text = delay.sms_text
        delay.substitution_info = "[[flight]]"
        delay.sms_text = "Not Used"
        delay.email_text = "Not Used"
        delay.save()

    notification_24 = AutomatedMessage.objects.filter(message_key=AutomatedMessage.FLIGHT_DEPARTURE_NOTIFICATION_24).first()
    if notification_24:
        notification_24.message_box_text = "Not Used"
        notification_24.substitution_info = "[[flight]], [[time]], [[oncallname]], [[flightdate]], [[flighttime]], [[origin-dest]], [[origin-directions-link]]"
        notification_24.save()

    notification_1 = AutomatedMessage.objects.filter(message_key=AutomatedMessage.FLIGHT_DEPARTURE_NOTIFICATION_1).first()
    if notification_1:
        notification_1.message_box_text = "Not Used"
        notification_1.substitution_info = "[[flight]], [[time]], [[oncallname]], [[flightdate]], [[flighttime]], [[origin-dest]], [[origin-directions-link]]"
        notification_1.save()


class Migration(migrations.Migration):

    dependencies = [
        ('announcements', '0005_insert_automated_messages'),
    ]

    operations = [
        migrations.AddField(
            model_name='automatedmessage',
            name='message_box_text',
            field=models.CharField(max_length=500, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='automatedmessage',
            name='substitution_info',
            field=models.CharField(max_length=500, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='automatedmessage',
            name='message_key',
            field=models.CharField(default=b'flight_dept_not_24', max_length=40, choices=[(b'flight_dept_not_24', b'Flight Departure 24 Hours '), (b'flight_dept_not_1', b'Flight Departure 1 Hour'), (b'flight_delay_not', b'Flight Delay'), (b'no_show_notification_member', b'(Member) Restricted due to No-shows'), (b'no_show_notification_admin', b'(Admin) Member Restricted due to No-shows')]),
        ),
        migrations.RunPython(load_data)
    ]
