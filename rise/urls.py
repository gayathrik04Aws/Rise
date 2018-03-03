from django.conf.urls import patterns, include, url
from django.views.generic import TemplateView
from django.conf import settings
from django.conf.urls.static import static

from accounts.views import LoggedIn

from django.contrib import admin

admin.autodiscover()

admin_urlpatterns = patterns(
    '',
    url(r'', include('accounts.admin_urls')),
    url(r'', include('flights.admin_urls')),
    url(r'', include('dashboard.admin_urls')),
    url(r'', include('reservations.admin_urls')),
    url(r'', include('announcements.admin_urls')),
    url(r'', include('billing.admin_urls')),
    url(r'', include('reports.admin_urls')),
    url(r'', include('anywhere.admin_urls')),
)

urlpatterns = patterns(
    '',
    url(r'^$', LoggedIn.as_view(), name='site_index'),

    url(r'', include('rise.redirect_urls')),

    url(r'^404/$', TemplateView.as_view(template_name='404.html'), name='404'),
    url(r'^500/$', TemplateView.as_view(template_name='500.html'), name='500'),
    url(r'^403/$', TemplateView.as_view(template_name='403.html'), name='403'),
    url(r'^auth-proxy.html', TemplateView.as_view(template_name='auth-proxy.html'), name='auth-proxy'),
    url(r'', include('accounts.urls')),
    url(r'', include('account_profile.urls')),
    url(r'', include('anywhere.urls')),
    url(r'', include('billing.urls')),
    url(r'', include('reservations.urls')),
    url(r'', include('flights.urls')),
    url(r'', include('support.urls')),

    url(r'^djangoadmin/', include(admin.site.urls)),
    url(r'^riseadmin/', include(admin_urlpatterns)),
)

if settings.STAGING or settings.DEBUG:
    urlpatterns += patterns(
        '',
        url(r'^robots.txt$', TemplateView.as_view(template_name='staging-robots.txt'),
            name='robots.txt'),
    )

if settings.PRODUCTION:
    urlpatterns += patterns(
        '',
        url(r'^robots.txt$', TemplateView.as_view(template_name='robots.txt'), name='robots.txt'),
    )

if settings.DEBUG:
    urlpatterns += patterns(
        '',
        url(r'', include('htmlmailer.urls')),
    )

    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
