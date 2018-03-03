from .conf import settings
from django.core.mail.backends.smtp import EmailBackend
from django.core.mail.message import sanitize_address

import smtplib


class WhitelistEmailBackend(EmailBackend):

    def _send(self, email_message):
        """A helper method that does the actual sending."""
        if not email_message.recipients():
            return False
        from_email = sanitize_address(email_message.from_email, email_message.encoding)
        recipients = [sanitize_address(addr, email_message.encoding)
                      for addr in email_message.recipients()]

        email_message.to = [addr for addr in email_message.to if self.check_email(addr)]
        email_message.cc = [addr for addr in email_message.cc if self.check_email(addr)]
        email_message.bcc = [addr for addr in email_message.bcc if self.check_email(addr)]

        if not email_message.to and not email_message.cc and not email_message.bcc:
            return False

        message = email_message.message()
        try:
            self.connection.sendmail(from_email, recipients, message.as_bytes(linesep='\r\n'))
        except smtplib.SMTPException:
            if not self.fail_silently:
                raise
            return False
        return True

    def check_email(self, email):
        """
        Return's True if this email is good to go when checked against the whitelist
        """
        for domain in settings.HTMLMAILER_DOMAIN_WHITELIST:
            if email.lower().endswith(domain.lower()):
                return True
        return False
