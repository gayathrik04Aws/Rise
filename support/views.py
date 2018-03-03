from django.views.generic import View
from django.core.mail import send_mail
from django.contrib import messages
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt


class TwilioCallForward(View):
    """
    XML response to forward calls from Twilio to the Rise Support number
    """

    def get(self, request, *args, **kwargs):
        return render(request, 'support/twilio-call-forward.xml', content_type="application/xml")


class TwilioSmsForward(View):
    """
    XML response to forward SMS items from Twilio to the Rise contact email address
    """
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super(TwilioSmsForward, self).dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        from_number = request.POST.get('From', None)
        to_number = request.POST.get('To', None)
        body = request.POST.get('Body', None)

        if from_number and to_number and body:
            subject = 'An SMS message from %s' % from_number
            message_body = "You have received an SMS message from %s:\n\n%s"  % (from_number, body)
            send_mail(subject, message_body, 'info@iflyrise.com', ['support@iflyrise.com',], )

            message = 'Thank you for your message.'
        else:
            message = 'Error receiving SMS message.'

        return render(request, 'support/twilio-sms-to-email.xml', {'message': message }, content_type="application/xml")
