from importlib import import_module

from django.conf import settings
from django.contrib.sites.models import Site


class ConstWrapper(object):
    def __init__(self, app_name):
        """
        A wrapper object that provides read-only access to an app's const module.

        Only CONST_LIKE_NAMES may be read.
        """
        self.app_name = app_name
        self._module = import_module('%s.const' % app_name)

    def __getattr__(self, item):
        item = item.upper()

        if not hasattr(self._module, item):
            valid_keys = [k for k in self._module.__dict__.keys() if k == k.upper() and not k.startswith('_')]
            raise ValueError('%s.%s is not a valid const [valid: %s]' % (self.app_name, item, ','.join(valid_keys)))

        return getattr(self._module, item)


class ConstHandler(object):
    """
    Provide secure access to <app>/const.py constants via template context.
    """
    def __getattr__(self, item):
        val = ConstWrapper(item)
        setattr(self, item, val)
        return val
ConstHandler = ConstHandler()


def context_settings(request):
    """
    Injects settings into the context
    """
    ret = {
        'STAGING': settings.STAGING,
        'PRODUCTION': settings.PRODUCTION,
        'site': Site.objects.get_current(),
        # make const.py modules availble via {{ const.<app_name>.<CONSTANT> }}
        # e.g. {{ const.flights.SHARING_OPTION_PUBLIC }}
        'const': ConstHandler
    }

    ret.update(settings.DEFAULT_MAILER_CONTEXT)

    return ret


