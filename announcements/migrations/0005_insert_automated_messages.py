from __future__ import unicode_literals
from django.db import migrations
from announcements.models import AutomatedMessage

def load_data(apps, schema_editor):
    automated_message = AutomatedMessage()
    automated_message.message_key = AutomatedMessage.FLIGHT_DEPARTURE_NOTIFICATION_24
    automated_message.sms_text = 'Flight [[flight]] departs at [[time]]. Need help? Call 844-359-7473 ext 1 and ask for [[oncallname]]'
    automated_message.email_text = 'Your RISE flight on [[flightdate]] from [[origin-dest]] is right around the corner. Please arrive 20 minutes before your scheduled [[flighttime]] departure. Contact us at 844-359-7473 ext. 1 if there is anything we can do to make your travel better.Click here for directions to RISE.[[origin-directions-link]]'
    automated_message.save()

    automated_message = AutomatedMessage()
    automated_message.message_key = AutomatedMessage.FLIGHT_DEPARTURE_NOTIFICATION_1
    automated_message.sms_text = 'Flight [[flight]] departs at [[time]]. Need help? Call 844-359-7473 ext 1 and ask for [[oncallname]]'
    automated_message.email_text = 'Good news! Your [[flighttime]] RISE flight from [[origin-dest]] is on time. Please arrive by [[airportarrivaltime]] so we can quickly check you in and get you on your way. Your RISE Rep, [[oncallname]], has everything ready for your arrival. Please contact us at 844-359-7473 ext 1 if your plans have changed.Click here for directions to RISE.[[origin-directions-link]]'
    automated_message.save()

    automated_message = AutomatedMessage()
    automated_message.message_key = AutomatedMessage.FLIGHT_DELAY_NOTIFICATION
    automated_message.sms_text = 'Flight [[flight]] has been delayed.'
    automated_message.save()

class Migration(migrations.Migration):
    dependencies = [
        ('announcements', '0004_automatedmessage')
      ]

    operations = [
        migrations.RunPython(load_data)
    ]
