from django.conf.urls import patterns, url

from . import admin_views as views

from flights.admin_forms import AnywhereOutboundFlightCreationForm, AnywhereReturnFlightCreationForm
from flights.admin_views import AdminCreateAnywhereFlightSetView, show_anywhere_flight_return_form

anywhere_wizard_forms = [AnywhereOutboundFlightCreationForm,AnywhereReturnFlightCreationForm]

urlpatterns = patterns('',
    url(r'^airports/$', views.AdminAirportListView.as_view(), name='admin_airports'),
    url(r'^airports/add/$', views.AdminCreateAirportView.as_view(), name='admin_add_airport'),
    url(r'^airports/(?P<pk>\d+)/$', views.AdminAirportDetailView.as_view(), name='admin_airport'),
    url(r'^airports/(?P<pk>\d+)/audit/$', views.AdminAirportAuditView.as_view(), name='admin_airport_audit'),
    url(r'^airports/(?P<pk>\d+)/edit/$', views.AdminEditAirportView.as_view(), name='admin_edit_airport'),

    url(r'^planes/$', views.AdminPlaneListView.as_view(), name='admin_planes'),
    url(r'^planes/add/$', views.AdminCreatePlaneView.as_view(), name='admin_add_plane'),
    url(r'^planes/(?P<pk>\d+)/$', views.AdminPlaneDetailView.as_view(), name='admin_plane'),
    url(r'^planes/(?P<pk>\d+)/audit/$', views.AdminPlaneAuditView.as_view(), name='admin_plane_audit'),
    url(r'^planes/(?P<pk>\d+)/edit/$', views.AdminEditPlaneView.as_view(), name='admin_edit_plane'),
    url(r'^planes/(?P<pk>\d+)/delete/$', views.AdminPlaneDeleteView.as_view(), name='admin_delete_plane'),


    url(r'^flights/(?P<pk>\d+)/edit/$', views.AdminEditFlightView.as_view(), name='admin_edit_flight'),
    url(r'^flights/(?P<pk>\d+)/edit/anywhere/$', views.AdminEditAnywhereFlightView.as_view(), name='admin_edit_anywhere_flight'),

    url(r'^flights/add/$', views.AdminCreateFlightView.as_view(), name='admin_add_flight'),
    url(r'^flights/add/anywhere/(?P<pk>\d+)$',
        views.AdminCreateAnywhereFlightSetView.as_view(anywhere_wizard_forms,
                                                       condition_dict={'1':show_anywhere_flight_return_form}), name='admin_add_anywhere_flightset'),
    url(r'^flights/anywhere/new/$', views.AdminNewAnywhereFlightSetView.as_view(), name='admin_new_anywhere'),
    url(r'^flights/export/$', views.ExportFlightsView.as_view(), name='admin_flights_export'),
    url(r'^flights/load/$', views.FlightLoadFactorView.as_view(), name='admin_flights_load'),
    url(r'^flights/(?P<pk>\d+)/$', views.AdminFlightDetailView.as_view(), name='admin_flight_detail'),
    url(r'^flights/(?P<pk>\d+)/reservations/$', views.AdminFlightAnywhereReservationsView.as_view(), name='admin_anywhere_flight_reservations'),
    url(r'^flights/(?P<pk>\d+)/audit/$', views.AdminFlightAuditView.as_view(), name='admin_flight_audit'),
    url(r'^flights/(?P<pk>\d+)/cancel/$', views.AdminFlightCancelView.as_view(), name='admin_flight_cancel'),
    url(r'^flights/(?P<pk>\d+)/delay/$', views.AdminFlightDelayedView.as_view(), name='admin_flight_delay'),
    url(r'^flights/(?P<pk>\d+)/delete/$', views.AdminFlightDeleteView.as_view(), name='admin_flight_delete'),
    url(r'^flights/(?P<pk>\d+)/marketing/$', views.AdminFlightMarketingView.as_view(), name='admin_flight_marketing'),
    url(r'^flights/(?P<pk>\d+)/book/$', views.AdminFlightBookMemberView.as_view(), name='admin_flight_book_member'),
    url(r'^flights/(?P<pk>\d+)/book/(?P<member_pk>\d+)$', views.AdminFlightBookMemberConfirmView.as_view(), name='admin_flight_book_member_confirm'),
    url(r'^flights/anywhere/(?P<pk>\d+)/book/$', views.AdminAnywhereFlightBookMemberView.as_view(), name='admin_anywhere_flight_book_member'),
    url(r'^flights/anywhere/(?P<flightset_pk>\d+)/book/(?P<member_pk>\d+)/(?P<reservation_pk>\d+)/$', views.AdminAnywhereFlightBookMemberConfirmView.as_view(), name='admin_anywhere_flight_book_member_confirm'),
    url(r'^flights/book/pay/(?P<pk>\d+)/$', views.AdminFlightBookMemberPayView.as_view(), name='admin_flight_book_member_pay'),
    url(r'^flights/book/cancel/(?P<pk>\d+)/$', views.AdminFlightBookMemberCancelView.as_view(), name='admin_flight_book_member_cancel'),
    url(r'^flights/book/cancel/(?P<pk>\d+)/passenger/(?P<passenger_id>\d+)/$', views.AdminFlightBookMemberCancelView.as_view(), name='admin_flight_book_member_passenger_cancel'),
    url(r'^flights/book/cancel/anywhere/(?P<pk>\d+)/(?P<passenger_id>\d+)/$', views.AdminFlightAnywherePassengerCancelView.as_view(), name='admin_flight_anywhere_passenger_cancel'),
    url(r'^flights/book/success/(?P<pk>\d+)/$', views.AdminFlightBookMemberSuccessView.as_view(), name='admin_flight_book_member_success'),
    url(r'^flights/$', views.AdminFlightListView.as_view(), name='admin_list_flights'),
    url(r'^flights/week/(?P<year>\d{4})/(?P<week>\d{1,2})/$', views.AdminFlightWeekView.as_view(), name='admin_list_flights_week'),
    url(r'^flights/month/(?P<year>\d{4})/(?P<month>\d{1,2})/$', views.AdminFlightMonthView.as_view(), name='admin_list_flights_month'),

    url(r'^flights/(?P<pk>\d+)/print/$', views.AdminFlightPrintManifestView.as_view(), name='admin_flight_print_manifest'),
    url(r'^flights/(?P<pk>\d+)/background-check/$', views.AdminFlightBackgroundCheckView.as_view(), name='admin_flight_background_check'),
    url(r'^flights/(?P<pk>\d+)/messages/add/$', views.AdminCreateFlightMessageView.as_view(), name='admin_flight_message'),

    url(r'^background-check/$', views.AdminFlightListBackgroundCheckView.as_view(), name='admin_background_check'),
    url(r'^background-check/update/(?P<flight_pk>\d+)/(?P<passenger_pk>\d+)/$', views.UpdateBackgroundCheckStatusView.as_view(), name='admin_background_check_update'),

    url(r'^routes/$', views.AdminRouteListView.as_view(), name='admin_list_routes'),
    url(r'^routes/add/$', views.AdminCreateRouteView.as_view(), name='admin_add_route'),
    url(r'^routes/(?P<pk>\d+)/$', views.AdminRouteView.as_view(), name='admin_route_detail'),
    url(r'^routes/(?P<pk>\d+)/edit/$', views.AdminEditRouteView.as_view(), name='admin_edit_route'),
    url(r'^routes/(?P<pk>\d+)/delete/$', views.AdminRouteDeleteView.as_view(), name='admin_delete_route'),
    url(r'^routes/(?P<route_pk>\d+)/routetime/add/$', views.AdminCreateRouteTimeView.as_view(), name='admin_add_routetime'),
    url(r'^routes/(?P<route_pk>\d+)/routetime/(?P<pk>\d+)/edit/$', views.AdminEditRouteTimeView.as_view(), name='admin_edit_routetime'),
    url(r'^routes/(?P<route_pk>\d+)/routetime/(?P<pk>\d+)/delete/$', views.AdminRouteTimeDeleteView.as_view(), name='admin_delete_routetime'),

    url(r'^routes/select/$', views.AdminRouteSelectFlightsView.as_view(), name='admin_routes_select_flights'),
)
