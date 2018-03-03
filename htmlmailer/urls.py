from django.conf.urls import patterns, url

from . import views

urlpatterns = patterns('',
    url(r'^email/preview/(?P<template>.*)$', views.EmailPreviewView.as_view(), name='email_preview'),
)
