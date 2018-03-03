from django.conf.urls import patterns, url
from django.conf import settings
from django.views.generic.base import RedirectView


wp_roots = [
    'about', 'faq', 'legal', 'press', 'terms', 'privacy', 'membership', 'blog'
]

urlpatterns = patterns(
    '',
    *(
        url(r'^{}/$'.format(r), RedirectView.as_view(url='/'.join((settings.WP_URL, r)), permanent=True))
        for r in wp_roots
    )
)
