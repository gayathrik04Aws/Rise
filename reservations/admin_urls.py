from django.conf.urls import patterns, url

from . import admin_views as views


urlpatterns = patterns('',
    url(r'^reservations/flight/(?P<pk>\d+)/$', views.AdminFlightReservationDetailView.as_view(),
        name='admin_flight_reservation'),
    url(r'^reservations/waitlist/(?P<pk>\d+)/book/$', views.AdminBookFromWaitlistView.as_view(),
        name='admin_book_from_waitlist'),
    url(r'^reservations/book/companions/(?P<pk>\d+)/$', views.AdminCompanionSelectionView.as_view(), name='admin_book_companions'),
    url(r'^reservations/book/confirmed/$', views.AdminBookConfirmationView.as_view(), name='admin_book_confirmed'),
    url(r'^reservations/book/confirm/$', views.AdminBookConfirmView.as_view(), name='admin_book_confirm'),
    url(r'^reservations/book/reserve/$', views.AdminConfirmReservationView.as_view(), name='admin_book_reserve'),
    url(r'^reservations/book/cancel/$', views.AdminCancelBookingView.as_view(), name='admin_book_cancel'),
    url(r'^reservations/export/$', views.ExportReservationsView.as_view(), name='admin_reservations_export'),
    url(r'^reservations/export/date/$', views.ExportReservationsViewByDate.as_view(), name='admin_reservations_export_by_date'),
    url(r'^waitlist/$', views.AdminFlightWaitlistListView.as_view(), name='admin_list_waitlist'),
    url(r'^waitlist/export/$', views.ExportWaitListView.as_view(), name='admin_waitlist_export'),
    url(r'^waitlist/(?P<pk>\d+)/delete/$', views.AdminFlightWaitlistDeleteView.as_view(), name='admin_waitlist_delete'),
    url(r'^passenger/(?P<pk>\d+)/checkin/$', views.CheckInPassenger.as_view(), name='admin_passenger_checkin'),
)
