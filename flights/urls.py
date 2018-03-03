from django.conf.urls import patterns, url

from . import views

urlpatterns = patterns('',
    url(r'^flight/(?P<pk>\d+)/feedback/$', views.FlightFeedbackView.as_view(), name='flight_feedback'),
)
