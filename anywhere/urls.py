from django.conf.urls import url, patterns

from . import views

urlpatterns = patterns(
    '',
    url(r'^anywhere/$', views.AnywhereFlightRequestCreateView.as_view(), name='anywhere_index'),
    url(r'^anywhere/(?P<pk>\d+)/$', views.AnywhereFlightRequestRouteView.as_view(), name='anywhere_route'),
    url(r'^anywhere/(?P<pk>\d+)/dates/$', views.AnywhereFlightRequestDatesView.as_view(), name='anywhere_dates'),
    url(r'^anywhere/(?P<pk>\d+)/passengers/$', views.AnywhereFlightRequestPassengersView.as_view(),
        name='anywhere_passengers'),
    url(r'^anywhere/(?P<pk>\d+)/summary/$', views.AnywhereFlightRequestSummary.as_view(), name='anywhere_summary'),
    url(r'^anywhere/(?P<slug>[\w-]+)/detail$', views.AnywhereFlightInfoView.as_view(), name='anywhere_flight_info'),

    url(r'^anywhere/(?P<slug>[\w-]+)/invite/view$', views.ViewInviteRedirectView.as_view(), name='view_anywhere_invite'),
    url(r'^anywhere/(?P<slug>[\w-]+)/join$', views.JoinAnywhereRedirectView.as_view(), name='join_anywhere'),
    url(r'^anywhere/(?P<slug>[\w-]+)/invite$', views.AnywhereInvitationView.as_view(), name='invite_anywhere'),
    url(r'^anywhere/(?P<slug>[\w-]+)/invite/send$', views.AnywhereSendInvitationsView.as_view(),
        name='email_invitations'),
    url(r'^anywhere/flights/available/(?P<page>\d+)/$', views.AnywhereAvailableFlightListView.as_view(), name='available_flights'),
    url(r'^anywhere/learn/$', views.AnywhereLearnView.as_view(), name='learn_anywhere'),
    url(r'^anywhere/upgrade/$', views.AnywhereUpgradeView.as_view(), name='anywhere_upgrade')
)
