from django.conf.urls import patterns, url

from . import admin_views as views


urlpatterns = patterns('',

    url(r'^billing/export/charges/$', views.ExportChargesView.as_view(), name='admin_billing_export_charges'),
    url(r'^billing/transaction/testharness/$', views.TransactionTestHarnessView.as_view(), name='admin_test_transaction_harness'),

)
