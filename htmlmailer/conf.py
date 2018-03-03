from django.conf import settings
from appconf import AppConf


class HtmlmailerConf(AppConf):
    DOMAIN_WHITELIST = []

    class Meta:
        prefix = 'htmlmailer'
