from __future__ import absolute_import

import mailchimp
from celery import shared_task
from django.conf import settings


@shared_task
def mailchimp_subscribe(list_id, email, merge_vars, double_optin=False):
    try:
        mc = mailchimp.Mailchimp(settings.MAILCHIMP_API_KEY)
        mc.lists.subscribe(list_id, {'email': email}, merge_vars=merge_vars, update_existing=True, double_optin=double_optin)
    except:
        pass


@shared_task
def mailchimp_unsubscribe(list_id, email):
    try:
        mc = mailchimp.Mailchimp(settings.MAILCHIMP_API_KEY)
        mc.lists.unsubscribe(list_id, {'email': email}, delete_member=False, send_goodbye=False, send_notify=False)
    except:
        pass
