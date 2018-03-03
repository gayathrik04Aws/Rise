from django.db import models, transaction
from django.conf import settings

class Announcement(models.Model):
    """
    System-wide updates/announcements

    title: the announcement title (optional)
    message: The announcement message body
    url: URL to more information
    created: when this announcement was created
    created_by: the user that created this announcement
    """
    title = models.CharField(max_length=128, null=True, blank=True)
    message = models.CharField(max_length=256)
    link_name = models.CharField(max_length=64, null=True, blank=True)
    link = models.URLField(max_length=512, null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ['-created']

    def __unicode__(self):
        return self.title if self.title else 'Announcement #%d' % self.pk


class AutomatedMessage(models.Model):
    '''
    Slight misnomer as this is for any message that we are letting the RISE staff configure the text for.
    '''

    FLIGHT_DEPARTURE_NOTIFICATION_24 = 'flight_dept_not_24'
    FLIGHT_DEPARTURE_NOTIFICATION_1 = 'flight_dept_not_1'
    FLIGHT_DELAY_NOTIFICATION = 'flight_delay_not'
    NO_SHOW_RESTRICTION_MEMBER = 'no_show_notification_member'
    NO_SHOW_RESTRICTION_ADMIN = 'no_show_notification_admin'

    MESSAGE_KEY_CHOICES=(
        (FLIGHT_DEPARTURE_NOTIFICATION_24,'Flight Departure 24 Hours '),
        (FLIGHT_DEPARTURE_NOTIFICATION_1,'Flight Departure 1 Hour'),
        (FLIGHT_DELAY_NOTIFICATION,'Flight Delay'),
        (NO_SHOW_RESTRICTION_MEMBER, '(Member) Restricted due to No-shows'),
        (NO_SHOW_RESTRICTION_ADMIN, '(Admin) Member Restricted due to No-shows')

    )
    message_key = models.CharField(max_length=40,choices=MESSAGE_KEY_CHOICES, default=FLIGHT_DEPARTURE_NOTIFICATION_24)
    # use the following two fields for keys that are for email messages.
    sms_text = models.CharField(max_length=160,null=True, blank=True)
    email_text = models.CharField(max_length=500,null=True, blank=True)
    # use this field for messages that aren't emailed/texted but are shown on screen.
    message_box_text = models.CharField(max_length=500,null=True, blank=True)
    substitution_info = models.CharField(max_length=500,null=True, blank=True)
