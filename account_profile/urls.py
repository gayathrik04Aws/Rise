from django.conf.urls import patterns, url

from . import views

urlpatterns = patterns('',
    url(r'^member/$', views.DashboardView.as_view(), name='dashboard'),
    url(r'^flight/reservations/(?P<status>(upcoming|complete|all))/$', views.ReservationsView.as_view(), name='reservations'),
    url(r'^flight/reservations/(?P<pk>\d+)/$', views.ReservationDetailView.as_view(), name='reservation_detail'),
    url(r'^flight/reservations/(?P<pk>\d+)/ical.ics$', views.FlightReservationiCalView.as_view(), name='flight_reservation_ical'),
    url(r'^reservations/(?P<pk>\d+)/ical.ics$', views.ReservationiCalView.as_view(), name='reservation_ical'),
    url(r'^reservations/(?P<pk>\d+)/email/$', views.ReservationEmailView.as_view(), name='reservation_email'),
    url(r'^flight/waitlists/(?P<pk>\d+)/cancel/$', views.CancelWaitlistView.as_view(), name='waitlists_cancel'),
    url(r'^profile/$', views.ProfileView.as_view(), name='profile'),
    url(r'^profile/contract/$', views.ContractView.as_view(), name='contract_view'),
    url(r'^profile/edit/$', views.EditProfileView.as_view(), name='profile_edit'),
    url(r'^profile/avatar/$', views.UpdateAvatarView.as_view(), name='profile_avatar'),
    url(r'^profile/plan/$', views.PlanOptionsView.as_view(), name='profile_plan'),
    url(r'^profile/plan/change/$', views.ChangePlanView.as_view(), name='profile_plan_change'),
    url(r'^profile/plan/change/(?P<pk>\d+)/$', views.ChangePlanView.as_view(), name='profile_plan_change'),
    url(r'^profile/plan/upgrade/(?P<plan>(Executive|Chairman))/$', views.UpgradePlanView.as_view(), name='profile_plan_upgrade'),
    url(r'^profile/billing/$', views.BillingInfoView.as_view(), name='profile_billing'),
    url(r'^profile/billing/method/(?P<pk>\d+)/$', views.PaymentMethodView.as_view(), name='profile_payment_method'),
    url(r'^profile/billing/card/$', views.UpdateCreditCardView.as_view(), name='profile_billing_card'),
    url(r'^profile/billing/card/delete/(?P<pk>\d+)/$', views.DeleteCreditCardView.as_view(), name='profile_billing_delete_card'),
    url(r'^profile/billing/bank-account/$', views.BankAccountView.as_view(), name='profile_billing_bank_account'),
    url(r'^profile/billing/bank-account/delete/(?P<pk>\d+)/$', views.DeleteBankAccountView.as_view(), name='profile_billing_bank_account_delete'),
    url(r'^profile/billing/bank-account/verify/$', views.BankAccountVerifyView.as_view(), name='profile_billing_bank_account_verify'),
    url(r'^profile/billing/history/$', views.ChargeListView.as_view(), name='profile_billing_history'),
    url(r'^profile/invitations/$', views.InvitationsView.as_view(), name='profile_invitations'),
    url(r'^profile/invitations/request/$', views.RequestInvitationsView.as_view(), name='profile_request_invitations'),
    url(r'^profile/invitations/send/$', views.SendInvitationView.as_view(), name='profile_send_invitation'),
    url(r'^profile/notifications/$', views.NotificationsView.as_view(), name='profile_notifications'),
    url(r'^profile/companions/$', views.CompanionsView.as_view(), name='profile_companions'),
    url(r'^profile/companions/add/$', views.AddCompanionView.as_view(), name='profile_companions_add'),
    url(r'^profile/companions/(?P<pk>\d+)/edit/$', views.EditCompanionView.as_view(), name='profile_companions_edit'),
    url(r'^profile/companions/(?P<pk>\d+)/delete/$', views.DeleteCompanionView.as_view(), name='profile_companions_delete'),
    url(r'^profile/members/$', views.MembersListView.as_view(), name='profile_members'),
    url(r'^profile/members/(?P<pk>\d+)/delete/$', views.DeleteMemberView.as_view(), name='profile_members_delete'),
    url(r'^profile/members/(?P<pk>\d+)/reservations/$', views.MemberReservationsListView.as_view(), name='profile_members_reservations'),
    url(r'^profile/members/add/$', views.AddMemberView.as_view(), name='profile_members_add'),
    url(r'^profile/members/(?P<pk>\d+)/edit/$', views.EditMemberView.as_view(), name='profile_members_edit'),
    url(r'^profile/members/(?P<pk>\d+)/update-permissions/$', views.UpdateUserPermissions.as_view(), name='profile_members_update_permissions'),
    url(r'^profile/personal-info/$', views.PersonalInfoView.as_view(), name='profile_personal_info'),
    url(r'^profile/update-origin/$', views.UpdateOriginAirportView.as_view(), name='profile_update_origin'),
)
