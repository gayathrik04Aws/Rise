from django.test import TestCase
from django.test.utils import override_settings
from django.core import mail


@override_settings(EMAIL_BACKEND='htmlmailer.backends.WhitelistEmailBackend', HTMLMAILER_DOMAIN_WHITELIST=['mobelux.com'])
class WhitelistEmailBackendTestCase(TestCase):

    def test_sending_email(self):
        # Send message.
        sent = mail.send_mail('Subject here', 'Here is the message.', 'jemerick@gmail.com', ['jemerick@gmail.com'], fail_silently=False)

        # Test that one message has been sent.
        self.assertEqual(sent, 0)

        # Send message.
        sent = mail.send_mail('Subject here', 'Here is the message.', 'jemerick@gmail.com', ['jason@mobelux.com'], fail_silently=False)

        # Test that one message has been sent.
        self.assertEqual(sent, 1)

        # Send message.
        sent = mail.send_mail('Subject here', 'Here is the message.', 'jemerick@gmail.com', ['jason@mobelux.com', 'jemerick@gmail.com'], fail_silently=False)

        # Test that one message has been sent.
        self.assertEqual(sent, 1)

        # Send message.
        sent = mail.send_mail('Subject here', 'Here is the message.', 'jemerick@gmail.com', ['jason@MoBeLuX.cOm'], fail_silently=False)

        # Test that one message has been sent.
        self.assertEqual(sent, 1)

        # Send message.
        sent = mail.send_mail('Subject here', 'Here is the message.', 'jemerick@gmail.com', ['jason@mobelux.com', 'sarah@mobelux.com'], fail_silently=False)

        # Test that one message has been sent.
        self.assertEqual(sent, 1)
