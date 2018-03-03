from django.conf.urls import patterns, url
from django.core.urlresolvers import reverse_lazy
from django.views.generic.base import RedirectView

from . import admin_views as views


urlpatterns = patterns(
    '',
    url(r'^anywhere/$', RedirectView.as_view(url=reverse_lazy('admin_anywhere_pending')), name='admin_anywhere'),

    url(r'^anywhere/pending/$', views.AdminAnywherePendingRequestList.as_view(), name='admin_anywhere_pending'),
    url(r'^anywhere/ready/$', views.AdminAnywhereReadyRequestList.as_view(), name='admin_anywhere_ready'),
    url(r'^anywhere/unconfirmed/$', views.AdminAnywhereUnconfirmedRequestList.as_view(), name='admin_anywhere_unconfirmed'),
     url(r'^anywhere/confirmed/$', views.AdminAnywhereConfirmedRequestList.as_view(), name='admin_anywhere_confirmed'),
    url(r'^admin/anywhere/(?P<pk>\d+)/reservations/confirm/$', views.AdminConfirmAnywhereReservationsView.as_view(), name='admin_confirm_anywhere_reservations'),
    url(r'^admin/anywhere/(?P<pk>\d+)/reservations/refund/$', views.AdminProcessAnywhereRefundsView.as_view(), name='admin_process_anywhere_refunds'),
    url(r'^anywhere/(?P<pk>\d+)/(?P<pk_type>\w+)/message/$', views.AdminAnywhereRequestSendMessage.as_view(), name='admin_anywhere_send_message'),
    url(r'^anywhere/routes/$', views.AnywhereAdminRouteListView.as_view(), name='anywhere_admin_list_routes'),
    url(r'^anywhere/routes/add/$', views.AnywhereAdminCreateRouteView.as_view(), name='anywhere_admin_add_route'),
    url(r'^anywhere/routes/(?P<pk>\d+)/$', views.AnywhereAdminRouteView.as_view(), name='anywhere_admin_route_detail'),
    url(r'^anywhere/routes/(?P<pk>\d+)/edit/$', views.AnywhereAdminEditRouteView.as_view(), name='anywhere_admin_edit_route'),
    url(r'^anywhere/routes/(?P<pk>\d+)/delete/$', views.AnywhereAdminRouteDeleteView.as_view(), name='anywhere_admin_delete_route'),
)
