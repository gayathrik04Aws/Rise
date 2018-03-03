from django.conf.urls import patterns, url

from . import admin_views as views

urlpatterns = patterns('',
    url(r'^announcements/$', views.AdminAnnouncementListView.as_view(), name='admin_announcements_list'),
    url(r'^announcements/add/$', views.AdminAnnouncementCreateView.as_view(), name='admin_announcements_add'),
    url(r'^announcements/(?P<pk>\d+)/$', views.AdminAnnouncementDetailView.as_view(), name='admin_announcements_detail'),
    url(r'^announcements/(?P<pk>\d+)/edit/$', views.AdminAnnouncementUpdateView.as_view(), name='admin_announcements_update'),
    url(r'^announcements/(?P<pk>\d+)/delete/$', views.AdminAnnouncementDeleteView.as_view(), name='admin_announcements_delete'),
    url(r'^announcements/messagekey$', views.MessageChoicesView.as_view(), name='automated_message_key'),
)
