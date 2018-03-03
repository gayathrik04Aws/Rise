from django.conf.urls import patterns, url

from . import views

urlpatterns = patterns('',
    url(r'^stripe/webhook/$', views.StripeWebhookView.as_view(), name='stripe_webhook'),
    url(r'^braintree/webhook/$', views.BraintreeWebhookView.as_view(), name='braintree_webhook'),
)
