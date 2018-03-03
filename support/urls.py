from django.conf.urls import patterns, url

from . import views

urlpatterns = patterns('',
    url(r'^twilio/forward/$', views.TwilioCallForward.as_view(), name='twilio_forward'),
    url(r'^twilio/sms/$', views.TwilioSmsForward.as_view(), name='twilio_sms'),
)
