from django.conf.urls import patterns, url
from django.views.generic import TemplateView


urlpatterns = patterns('',
    url(r'^reports/$', TemplateView.as_view(template_name='admin/reports/reports.html'), name='admin_reports'),
)
