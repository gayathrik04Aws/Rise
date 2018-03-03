from django.conf.urls import patterns, url
from django.views.generic import TemplateView

from . import views
from .forms import PasswordChangeForm, PasswordResetForm, SetPasswordForm, LoginForm

urlpatterns = patterns('django.contrib.auth.views',
    url(r'^login/$', 'login', {'authentication_form': LoginForm}, name='login'),
    url(r'^login/anywhere/$', 'login', {'authentication_form': LoginForm, 'template_name':'registration/login_anywhere.html'}, name='login_anywhere'),
    url(r'^logout/$', 'logout', {'next_page': '/'}, name='logout'),
    url(r'^password/reset/$', 'password_reset', {'password_reset_form': PasswordResetForm}, name='password_reset'),
    url(r'^password/reset/done/$', 'password_reset_done', name='password_reset_done'),
    url(r'^password/reset/complete/$', 'password_reset_complete', name='password_reset_complete'),
    url(r'^password/reset/confirm/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$', 'password_reset_confirm', {'set_password_form': SetPasswordForm, 'post_reset_redirect': '/login/'}, name='password_reset_confirm'),
    url(r'^password/change/$', 'password_change', {'password_change_form': PasswordChangeForm, 'post_change_redirect': '/profile/'}, name='change_password'),
)

urlpatterns += patterns('',
    url(r'^logged-in/$', views.LoggedIn.as_view(), name="logged_in"),
    url(r'^sign-up/$', views.SignUpView.as_view(), name='invite_form'),
    url(r'^sign-up/anywhere/(?P<slug>[\w-]+)/$', views.SignUpAnywhereBasicView.as_view(), name='anywhere_invite_form'),
    url(r'^sign-up/intro/$', views.SignUpView.as_view(template_name='accounts/signup_intro.html'), name='invite_form_intro'),
    url(r'^sign-up/thanks/$', views.InviteThanksView.as_view(), name='invite_form_thanks'),
    url(r'^sign-up/(?P<code>[A-Z0-9]+)/$', views.InviteCodeView.as_view(), name='invite_code'),
    url(r'^sign-up/payment/$', views.PaymentFormView.as_view(), name='payment_form'),
    url(r'^sign-up/payment/anywhere/(?P<slug>[\w-]+)/$', views.PaymentAnywhereFormView.as_view(), name='payment_anywhere_form'),
    url(r'^sign-up/payment/anywhereplus/$', views.PaymentAnywherePlusView.as_view(), name='payment_anywhereplus'),
    url(r'^sign-up/payment/thanks/$', views.PaymentThanksView.as_view(), name='payment_form_thanks'),
    url(r'^sign-up/other/$', TemplateView.as_view(template_name='accounts/other_city_thanks.html'), name='other_city_thanks'),
    url(r'^notify/$', views.NotifyFormView.as_view(), name='notify'),
    url(r'^notify/intro/$', views.NotifyFormView.as_view(template_name='accounts/notify_intro.html'), name='notify_intro'),
    url(r'^notify/waitlist/$', views.NotifyWaitlistFormView.as_view(), name='notify_waitlist'),
    url(r'^landing/$', views.LandingFormView.as_view(), name='landing'),
    url(r'^events/$', views.LandingFormView.as_view(), name='events'),
    url(r'^corporate-sign-up/$', views.CorporateSignUpView.as_view(), name='corporate_invite_form'),
    url(r'^corporate-sign-up/confirm/$', views.CorporateSignUpConfirmView.as_view(), name='corporate_signup_form'),
    url(r'^corporate-sign-up/payment/$', views.CorporatePaymentView.as_view(), name='corporate_payment_form'),
    url(r'^corporate-sign-up/thanks/$', views.CorporateThanksView.as_view(), name='corporate_thanks'),
    url(r'^price-calculator/$', views.PriceCalculatorView.as_view(), name='price_calculator'),

    url(r'^register/(?P<pk>\d+)/(?P<signature>[_\w-]+)/$', views.RegisterLoginView.as_view(), name='register_login'),
    url(r'^register/account/$', views.RegisterAccountView.as_view(), name='register_account'),
    url(r'^register/anywhere/account/$', views.RegisterAnywhereBasicAccountView.as_view(), name='register_anywhere_account'),
    url(r'^register/payment/$', views.RegisterPaymentView.as_view(), name='register_payment'),
    url(r'^register/thanks/$', views.RegistrationThanksView.as_view(), name='register_thanks'),
    url(r'^register/member/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$', views.RegisterMemberFormView.as_view(), name='register_member'),

    url(r'^refer/$', views.ReferView.as_view(), name='refer_form'),
    url(r'^refer/thanks/$', views.ReferThanksView.as_view(), name='refer_thanks'),
)
