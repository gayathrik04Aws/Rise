from django.conf.urls import patterns, url

from . import views

urlpatterns = patterns('',

    url(r'^book/$', views.BookFromView.as_view(), name='book_from'),
    url(r'^book/(?P<plan>(executive|chairman))/$', views.BookFromView.as_view(), name='book_from'),
    url(r'^book/member/$', views.BookTeamMemberView.as_view(), name='book_team_member'),

    url(r'^book/companion/$', views.BookCompanionView.as_view(), name='book_companion_view'),
    url(r'^book/(?P<code>[\w]{3,4})/$', views.BookCalendarView.as_view(), name='book_when'),
    url(r'^book/(?P<code>[\w]{3,4})/(?P<year>[\d]{4})/(?P<month>[\d]{1,2})/$', views.BookCalendarView.as_view(), name='book_when_month'),
    url(r'^book/(?P<code>[\w]{3,4})/(?P<year>[\d]{4})/(?P<month>[\d]{1,2})/(?P<day>[\d]{1,2})/$', views.BookFlightsView.as_view(), name='book_flights'),
    url(r'^book/flight/waitlist/(?P<pk>\d+)/$', views.JoinFlightWaitlistView.as_view(), name='flight_waitlist'),
    url(r'^book/companions/(?P<pk>\d+)/$', views.CompanionSelectionView.as_view(), name='book_companions'),
    url(r'^book/companions/add/(?P<pk>\d+)/$', views.AddCompanionView.as_view(), name='book_add_companion'),
    url(r'^book/confirm/$', views.BookConfirmView.as_view(), name='book_confirm'),
    url(r'^book/reserve/$', views.ConfirmReservationView.as_view(), name='book_reserve'),
    url(r'^book/confirmed/$', views.BookConfirmationView.as_view(), name='book_confirmed'),
    url(r'^book/renew/$', views.BookRenewReservationView.as_view(), name='book_renew'),
    url(r'^book/remaining/$', views.ReservationTimeRemainingView.as_view(), name='book_remaining'),
    url(r'^book/cancel/$', views.CancelBookingView.as_view(), name='book_cancel'),
    url(r'^book/cancel/flight/(?P<pk>\d+)/$', views.CancelFlightReservationView.as_view(), name='book_cancel_flight_reservation'),
    url(r'^book/cancel/waitlist/(?P<pk>\d+)/$', views.FlightWaitlistCancelView.as_view(), name='cancel_waitlist'),
    url(r'^book/reschedule/flight/(?P<pk>\d+)/$', views.RescheduleFlightView.as_view(), name='book_reschedule_flight_reservation'),
    url(r'^book/similar/flight/(?P<flight_pk>\d+)/$', views.BookSimilarFlightsView.as_view(), name='book_similar_flights'),
    url(r'^book/similar/flightreservation/(?P<flightreservation_pk>\d+)/$', views.BookSimilarFlightsView.as_view(), name='book_similar_flights'),
    #url(r'^book/similar/flight/(?P<origin>[\w]{3,4})/(?P<destination>[\w]{3,4})/$', views.BookSimilarFlightsView.as_view(), name='book_similar_flights'),
    url(r'^book/flight/(?P<flight_pk>\d+)/$', views.BookFlightView.as_view(), name='book_flight'),
    url(r'^book/anywhere/(?P<slug>[\w-]+)/$', views.BookAnywhereView.as_view(), name='book_anywhere'),
    url(r'^book/anywhere/flight/(?P<pk>\d+)/$', views.BookAnywhereByFlightIDView.as_view(), name='book_anywhere_flight'),
    url(r'^book/anywhere/confirm/(?P<slug>[\w-]+)/$', views.BookAnywhereConfirmationView.as_view(), name='book_anywhere_confirmed'),
)
