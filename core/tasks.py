from __future__ import absolute_import

from smtplib import SMTPServerDisconnected
from celery import shared_task
from htmlmailer.mailer import send_html_email


@shared_task(default_retry_delay=30, max_retries=5, rate_limit="2/s")
def send_html_email_task(base_template, context, subject, from_email, recipient_list, attachments=None,
                         attachment_files=None, headers=None, connection=None, fail_silently=False, bcc=None):
    try:
        send_html_email(base_template, context, subject, from_email, recipient_list, attachments, attachment_files,
                        headers, connection, fail_silently, bcc)
    except SMTPServerDisconnected as exc:
        raise send_html_email_task.retry(exc=exc)
