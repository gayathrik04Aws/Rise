from django.conf.urls import patterns, url

from . import admin_views as views

urlpatterns = patterns('',
    url(r'^dashboard/$', views.AdminDashboardView.as_view(), name='admin_dashboard'),
    url(r'^$', views.AdminDashboardView.as_view(), name='admin_dashboard'),
)
