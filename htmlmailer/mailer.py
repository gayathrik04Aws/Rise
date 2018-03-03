from django.conf import settings
from django.contrib.sites.models import Site
from django.template.loader import render_to_string

from htmlmailer.message import EmailMultiAlternatives

from premailer import Premailer
import logging

logger = logging.getLogger(__name__)

def send_html_email(base_template, context, subject, from_email, recipient_list, attachments=None, attachment_files=None, headers=None, connection=None, fail_silently=False, bcc=None):
    """
    base_template: The base template path. NOTE: Does not include the `.html` or `.txt` extension. Those will be automatically appended.
    context: The context provided to the emails for rendering
    subject: The email subject
    from_email: The email to send from
    receipent_list: A list of emails to send this email to.
    attachments: A list of (filename, content, mimetype) triples to attach to the email.
    attachment_files: A list of file paths to attach to the email as an alternative to attachments.
    headers: A dictionary of extra headers to put on the message. The keys are the header name, values are the header values. It's up to the caller to ensure header names and values are in the correct format for an email message.
    connection: An email backend instance. Use this parameter if you want to use the same connection for multiple messages. If omitted, a new connection is created when send() is called.
    fail_silently: If True, exceptions raised while sending the message will be quashed.
    """

    html_template = '%s.html' % base_template
    text_template = '%s.txt' % base_template

    site = Site.objects.get_current()

    for k,v in settings.DEFAULT_MAILER_CONTEXT.iteritems():
        context.setdefault(k, v)

    # add site to context if not already provided
    if 'site' not in context:
        context.update({'site': site})

    if 'protocol' not in context:
        context.update({'protocol': settings.PROTOCOL})

    if 'subject' not in context:
        context.update({'subject': subject})

    html_message = render_to_string(html_template, context)
    text_message = render_to_string(text_template, context)

    base_url = '%s://%s' % (settings.PROTOCOL, site.domain)
    html_message = Premailer(html_message, base_url=base_url, strip_important=False, remove_classes=False, include_star_selectors=True).transform()


    email = EmailMultiAlternatives(subject, text_message, from_email, recipient_list, headers=headers, connection=connection, bcc=bcc)
    email.attach_alternative(html_message, 'text/html')

    if attachments is not None:
        for attachment in attachments:
            email.attach(*attachment)

    if attachment_files is not None:
        for filename in attachment_files:
            email.attach_file(filename)

    try:
        email.send(fail_silently)
    except Exception as e:
        logging.exception(e)

