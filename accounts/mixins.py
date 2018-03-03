from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.core.exceptions import ImproperlyConfigured
from django.http import HttpResponseRedirect
from django.utils.http import urlquote
from django.core.exceptions import PermissionDenied


class CsrfExemptMixin(object):

    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super(CsrfExemptMixin, self).dispatch(*args, **kwargs)


class LoginRequiredMixin(object):
    """
    View mixin which verifies that the user has authenticated.

    NOTE:
        This should be the left-most mixin of a view.
    """

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(LoginRequiredMixin, self).dispatch(*args, **kwargs)


class PermissionRequiredMixin(object):
    """
    View mixin which verifies that the logged in user has the specified
    permission.

    Class Settings
    `permission_required` - the permission name/list of permission names to check for.
    `login_url` - the login url of site
    `redirect_field_name` - defaults to "next"
    `raise_exception` - defaults to False - raise 403 if set to True

    Example Usage

        class SomeView(PermissionRequiredMixin, ListView):
            ...
            # required
            permission_required = "app.permission"

            # optional
            login_url = "/signup/"
            redirect_field_name = "hollaback"
            raise_exception = True
            ...
    """
    login_url = settings.LOGIN_URL
    permission_required = None
    raise_exception = True
    redirect_field_name = REDIRECT_FIELD_NAME

    def dispatch(self, request, *args, **kwargs):
        if type(self.permission_required) in (str, unicode):
            self.permission_required = [self.permission_required]

        if self.permission_required is None or len(self.permission_required) == 0:
            raise ImproperlyConfigured("'PermissionRequiredMixin' requires 'permission_required' attribute to be set.")

        for permission in self.permission_required:
            if len(permission.split('.')) != 2:
                raise ImproperlyConfigured('PermissionRequiredMixin requires all permission_required attributes to be set in the format `APP_NAME.PERMISSION` instead of %s' % (permission,))

        for permission in self.permission_required:
            if not request.user.has_perm(permission):
                if request.user.is_authenticated():
                    raise PermissionDenied
                else:
                    path = urlquote(request.get_full_path())
                    tup = self.login_url, self.redirect_field_name, path
                    return HttpResponseRedirect("%s?%s=%s" % tup)

        return super(PermissionRequiredMixin, self).dispatch(request, *args, **kwargs)


class PermissionRequiredAnyMixin(object):
    """
    View mixin which verifies that the logged in user has any (at least one) of the specified
    permission(s).

    Class Settings
    `permission_required` - the permission name/list of permission names to check for.
    `login_url` - the login url of site
    `redirect_field_name` - defaults to "next"
    `raise_exception` - defaults to False - raise 403 if set to True

    Example Usage

        class SomeView(PermissionRequiredMixin, ListView):
            ...
            # required
            permission_required = "app.permission"

            # optional
            login_url = "/signup/"
            redirect_field_name = "hollaback"
            raise_exception = True
            ...
    """
    login_url = settings.LOGIN_URL
    permission_required = None
    raise_exception = True
    redirect_field_name = REDIRECT_FIELD_NAME

    def dispatch(self, request, *args, **kwargs):
        if type(self.permission_required) in (str, unicode):
            self.permission_required = [self.permission_required]

        if self.permission_required is None or len(self.permission_required) == 0:
            raise ImproperlyConfigured("'PermissionRequiredMixin' requires 'permission_required' attribute to be set.")

        for permission in self.permission_required:
            if len(permission.split('.')) != 2:
                raise ImproperlyConfigured('PermissionRequiredMixin requires all permission_required attributes to be set in the format `APP_NAME.PERMISSION` instead of %s' % (permission,))

        has_permission = False
        for permission in self.permission_required:
            if request.user.has_perm(permission):
                has_permission = True
                break

        if not has_permission:
            if not request.user.has_perm(permission):
                if request.user.is_authenticated():
                    raise PermissionDenied
                else:
                    path = urlquote(request.get_full_path())
                    tup = self.login_url, self.redirect_field_name, path
                    return HttpResponseRedirect("%s?%s=%s" % tup)

        return super(PermissionRequiredAnyMixin, self).dispatch(request, *args, **kwargs)


class StaffRequiredMixin(object):
    login_url = settings.LOGIN_URL
    raise_exception = True
    redirect_field_name = REDIRECT_FIELD_NAME

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_staff:
            if request.user.is_authenticated():
                raise PermissionDenied
            else:
                path = urlquote(request.get_full_path())
                tup = self.login_url, self.redirect_field_name, path
                return HttpResponseRedirect("%s?%s=%s" % tup)

        return super(StaffRequiredMixin, self).dispatch(request, *args, **kwargs)
