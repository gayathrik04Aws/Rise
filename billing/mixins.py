from django.conf import settings
from django.core.exceptions import PermissionDenied


class TestHarnessAllowedMixin(object):

    def is_allowed(self):
        return settings.USE_TRANSACTION_HARNESS

    def dispatch(self, request, *args, **kwargs):

        if not self.is_allowed():
            raise PermissionDenied

        return super(TestHarnessAllowedMixin, self).dispatch(request, *args, **kwargs)
