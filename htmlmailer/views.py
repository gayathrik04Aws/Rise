from django.views.generic import View
from django.contrib.sites.models import Site
from django.template.loader import render_to_string
from django.template import TemplateDoesNotExist
from django.http import HttpResponse


import json
from premailer import Premailer


class EmailPreviewView(View):
    """
    Renders the HTML version of the email in a browser for testing/development
    """

    def is_html(self):
        return self.kwargs.get('template').endswith('html')

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        return self.render_to_response(context)

    def render_to_response(self, context):
        if self.is_html():
            content_type = 'text/html'
        else:
            content_type = 'text/text'

        content = render_to_string(self.get_template(), context)

        if self.is_html():
            base_url = '%s://%s' % (context.get('protocol'), context['site'].domain)
            content = Premailer(content, base_url=base_url, strip_important=False, remove_classes=False).transform()

        return HttpResponse(content, content_type=content_type)

    def get_template(self):
        """
        Get the name of the email template from the URL
        """
        template = self.kwargs.get('template')
        return template

    def get_json_context(self):
        template = self.kwargs.get('template')
        json_template = '.'.join(template.split('.')[:-1]) + '.json'

        try:
            return json.loads(render_to_string(json_template))
        except TemplateDoesNotExist:
            return {}

    def get_context_data(self, **kwargs):
        """
        Get the context for the email. Include the site and currently logged in
        user by default. Also include any GET parameters in the context as well.
        """
        context = self.get_json_context()

        user = None
        if self.request.user.is_authenticated():
            user = self.request.user

        if 'c' in self.request.GET:
            context_json = self.request.GET.get('c')
            context.update(json.loads(context_json))

        keys = self.request.GET.keys()
        for key in keys:
            if key in ('c',):
                continue
            context[key] = self.request.GET.get(key)

        context.update({
            'protocol': 'http',
            'site': Site.objects.get_current(),
            'user': user,
        })

        return context
