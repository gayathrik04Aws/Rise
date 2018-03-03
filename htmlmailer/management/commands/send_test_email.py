from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.core.mail.backends import smtp
from django.contrib.sites.models import Site
from django.contrib.auth import get_user_model
from django.template import TemplateDoesNotExist
from django.template.loader import render_to_string

import json
from optparse import make_option

from htmlmailer.mailer import send_html_email


class Command(BaseCommand):

    help = 'Sends a test email from django'

    option_list = BaseCommand.option_list + (
        make_option('-s', '--subject',
            action='store',
            dest='subject',
            type='string',
            default='Test Email Subject',
            help='The subject of the email'),

        make_option('-t', '--template',
            action='store',
            dest='template',
            type='string',
            help='The path of the template to render from without the extension. ex. "emails/invite"'),

        make_option('--to',
            action='store',
            dest='to',
            type='string',
            help='Email address of who to send the email to.'),

        make_option('-c', '--context',
            action='store',
            dest='context',
            type='string',
            default='{}',
            help='JSON object of the context to provide to the email templates.'),

        make_option('-l', '--litmus',
            action='store_true',
            dest='litmus',
            default=False,
            help='Automatically sends the test email to litmus for testing.'),
    )

    def handle(self, *args, **options):
        subject = options.get('subject')

        to_email = options.get('to')
        if options.get('litmus'):
            to_list = [to_email, 'mobelux@litmustest.com']
        else:
            to_list = [to_email]

        base_template = options.get('template')

        user = None
        try:
            UserModel = get_user_model()
            user = UserModel.objects.get(email=to_email)
        except:
            pass

        context = {
            'site': Site.objects.get_current(),
            'protocol': 'http',
            'user': user,
        }

        json_template = '%s.json' % base_template
        try:
            context_json = json.loads(render_to_string(json_template))
            context.update(context_json)
        except TemplateDoesNotExist:
            pass

        context_json = options.get('context')
        context_json = json.loads(context_json)
        context.update(context_json)

        backend = smtp.EmailBackend(host='smtp.mandrillapp.com', port=587, username='jason@mobelux.com', password='S0y3k8iVlNabZ7V_cmAB0Q')

        send_html_email(base_template, context, subject, settings.DEFAULT_FROM_EMAIL, to_list, fail_silently=False, connection=backend)

        print 'Email sent to %s' % ', '.join(to_list)
