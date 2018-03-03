from django.contrib import messages
from django.core.urlresolvers import reverse_lazy, reverse, NoReverseMatch
from django.views.generic import View, FormView, CreateView,DetailView,UpdateView,DeleteView
from django.shortcuts import redirect

from accounts.mixins import StaffRequiredMixin, PermissionRequiredMixin
import flights

from anywhere import models, admin_forms




# TODO: apply PermissionRequiredMixin
from anywhere.models import AnywhereFlightSet
from core.tasks import send_html_email_task
from reservations.models import ReservationError
from rise.util import FormListView


class AdminAnywherePendingRequestList(StaffRequiredMixin, FormListView):
    template_name = 'anywhere/admin/pending_list.html'
    queryset = models.ANYWHERE_PENDING_QUERYSET
    form_class = admin_forms.AnywhereFlightRequestActionForm
    success_url = reverse_lazy('admin_anywhere_pending')

    def form_valid(self, form):
        target = form.cleaned_data['target']

        if form.cleaned_data['action'] == admin_forms.AnywhereFlightRequestActionForm.ACTION_APPROVE:
            # change success URL.. real action happens after redirect
            self.success_url = reverse('admin_add_anywhere_flightset', kwargs={'pk': target.pk})
        elif form.cleaned_data['action'] == admin_forms.AnywhereFlightRequestActionForm.ACTION_DECLINE:
            target.decline()
            messages.success(self.request, 'Anywhere Flight Request Declined')

        return super(AdminAnywherePendingRequestList, self).form_valid(form)


class AdminAnywhereReadyRequestList(StaffRequiredMixin, FormListView):
    template_name = 'anywhere/admin/ready_list.html'
    form_class = admin_forms.AnywhereFlightSetActionForm
    queryset = models.AnywhereFlightSet.get_anywhere_ready_queryset()
    success_url = reverse_lazy('admin_anywhere_ready')

    def form_valid(self, form):
        target = form.cleaned_data['flightset']
        action = form.cleaned_data['flightset_action']

        if action == admin_forms.AnywhereFlightSetActionForm.FLIGHTSET_ACTION_CONFIRM:
            try:
                target.perform_confirmation(self.request.user)
            except ReservationError as err:
                messages.error(self.request, err.detailed_repr)
            else:
                messages.success(self.request, 'Anywhere Flight Confirmed')
        elif action == admin_forms.AnywhereFlightRequestActionForm.ACTION_MESSAGE:
            self.success_url = reverse('admin_anywhere_send_message', kwargs={'pk': target.pk})
        else:
            raise NotImplemented('FlightSet Action {} not implemented'.format(action))

        return super(AdminAnywhereReadyRequestList, self).form_valid(form)

class AdminAnywhereConfirmedRequestList(StaffRequiredMixin, FormListView):
    template_name = 'anywhere/admin/confirmed_list.html'
    form_class = admin_forms.AnywhereFlightSetActionForm
    queryset = models.AnywhereFlightSet.get_anywhere_confirmed_queryset()
    success_url = reverse_lazy('admin_anywhere_confirmed')

    def form_valid(self, form):
        target = form.cleaned_data['flightset']
        action = form.cleaned_data['flightset_action']

        if action == admin_forms.AnywhereFlightRequestActionForm.ACTION_MESSAGE:
            self.success_url = reverse('admin_anywhere_send_message', kwargs={'pk': target.pk})
        else:
            raise NotImplemented('FlightSet Action {} not implemented'.format(action))

        return super(AdminAnywhereConfirmedRequestList, self).form_valid(form)

class AdminAnywhereUnconfirmedRequestList(StaffRequiredMixin, FormListView):
    template_name = 'anywhere/admin/unconfirmed_list.html'
    form_class = admin_forms.AnywhereFlightSetUnconfirmedActionForm
    queryset = models.AnywhereFlightSet.get_anywhere_unconfirmed_queryset()
    success_url = reverse_lazy('admin_anywhere_unconfirmed')

    def form_valid(self, form):
        target = form.cleaned_data['flightset']
        action = form.cleaned_data['flightset_action']

        if action == admin_forms.AnywhereFlightSetActionForm.FLIGHTSET_ACTION_CONFIRM:
            try:
                target.perform_confirmation(self.request.user)
            except ReservationError as err:
                messages.error(self.request, err.detailed_repr)
            else:
                messages.success(self.request, 'Anywhere Flight Confirmed')
        elif action == admin_forms.AnywhereFlightRequestActionForm.ACTION_MESSAGE:
            self.success_url = reverse('admin_anywhere_send_message', kwargs={'pk': target.pk})
        else:
            raise NotImplemented('FlightSet Action {} not implemented'.format(action))

        return super(AdminAnywhereUnconfirmedRequestList, self).form_valid(form)


class AdminAnywhereRequestSendMessage(StaffRequiredMixin, FormView):
    template_name = 'anywhere/admin/send_message.html'
    form_class = admin_forms.AnywhereFlightRequestSendMessageForm

    def get_success_url(self):
        try:
            return reverse(self.request.GET.get('next', 'admin_anywhere'))
        except NoReverseMatch:
            return reverse('admin_anywhere')

    def get_initial(self):
        i = super(AdminAnywhereRequestSendMessage, self).get_initial()
        if self.kwargs['pk_type'] == "flight_set":
            flight_set = models.AnywhereFlightSet.objects.filter(id=self.kwargs['pk']).first()
            i.update({
                'flight_request': flight_set.anywhere_request_id
            })
        else:
            i.update({
                'flight_request': self.kwargs['pk']
            })
        return i

    def form_valid(self, form):
        form.send()
        messages.success(self.request, 'Message Sent')

        return super(AdminAnywhereRequestSendMessage, self).form_valid(form)

class AdminProcessAnywhereRefundsView(View):

    def post(self, *args, **kwargs):
        flightset_pk = self.kwargs["pk"]
        flightset = AnywhereFlightSet.objects.filter(id=flightset_pk).first()
        try:
            flightset.process_overpaid_passenger_refunds(self.request.user)
            messages.success(self.request, "Refunds processed successfully")
        except ReservationError as re:
            messages.error(self.request, re.message)
        return redirect(self.request.META['HTTP_REFERER'])

class AdminConfirmAnywhereReservationsView(View):
    def post(self, *args, **kwargs):
        flightset_pk = self.kwargs["pk"]
        flightset = AnywhereFlightSet.objects.filter(id=flightset_pk).first()
        try:
            flightset.complete_reservations(self.request.user)
            messages.success(self.request, "Reservations charged successfully")
        except ReservationError as re:
            messages.error(self.request, re.message)
        return redirect(self.request.META['HTTP_REFERER'])

class AnywhereAdminRouteListView(StaffRequiredMixin, PermissionRequiredMixin, FormView):
    """
    Displays a list of routes, with the option to make a selection from these
    for automated flight creation
    """
    permission_required = 'accounts.can_edit_flights'
    model = models.AnywhereRoute
    template_name = 'anywhere/admin/anywhere_route_list.html'
    form_class = admin_forms.AnywhereRouteListForm
    success_url = reverse_lazy('anywhere_admin_routes_select_flights')

    def get_context_data(self, **kwargs):
        context = super(AnywhereAdminRouteListView, self).get_context_data(**kwargs)

        context.update({
            'route_list': models.AnywhereRoute.objects.all(),
        })

        return context

    def form_valid(self, form):
        selected_routes = form.cleaned_data.get('route_list')
        start_date = form.cleaned_data.get('start_date')
        end_date = form.cleaned_data.get('end_date')

        self.request.session['selected_routes'] = [route.pk for route in selected_routes]
        self.request.session['start_date'] = str(start_date)
        self.request.session['end_date'] = str(end_date)

        return redirect(self.get_success_url())

class AnywhereAdminCreateRouteView(StaffRequiredMixin, PermissionRequiredMixin, CreateView):

    permission_required = 'accounts.can_edit_flights'
    template_name = 'flights/admin/route_form.html'
    form_class = admin_forms.AnywhereRouteForm
    model = models.AnywhereRoute

    def get_context_data(self, **kwargs):
        context = super(AnywhereAdminCreateRouteView, self).get_context_data(**kwargs)
        context.update({
            'anywherepath':True,
        })
        return context

    def get_success_url(self):
        return reverse('anywhere_admin_route_detail', args=[self.object.pk])

class AnywhereAdminRouteView(StaffRequiredMixin, PermissionRequiredMixin, DetailView):
    """
    View the details for the current flight
    """

    permission_required = 'accounts.can_edit_flights'
    template_name = 'flights/admin/route_detail.html'
    model = models.AnywhereRoute

    def get_context_data(self, **kwargs):
        context = super(AnywhereAdminRouteView, self).get_context_data(**kwargs)
        context.update({
            'route': self.object,
            'anywherepath':True,
        })
        return context

class AnywhereAdminEditRouteView(StaffRequiredMixin, PermissionRequiredMixin, UpdateView):


    permission_required = 'accounts.can_edit_flights'
    template_name = 'flights/admin/route_form.html'
    form_class = admin_forms.AnywhereRouteForm
    model = models.AnywhereRoute

    def get_context_data(self, **kwargs):
        context = super(AnywhereAdminEditRouteView, self).get_context_data(**kwargs)
        context.update({
            'route': self.object,
            'anywherepath':True,
        })
        return context

    def get_success_url(self):
        return reverse('anywhere_admin_route_detail', args=[self.object.pk])


class AnywhereAdminRouteDeleteView(StaffRequiredMixin, PermissionRequiredMixin, View):
    """
    Admin view to delete a route
    """
    permission_required = 'accounts.can_edit_flights'
    template_name = 'flights/admin/route_confirm_delete.html'
    success_url = reverse_lazy('anywhere_admin_list_routes')

    def get(self, request, *args, **kwargs):
        route = models.AnywhereRoute.objects.filter(id=self.kwargs.get('pk', None))
        if route:
            route.delete()
        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse_lazy('anywhere_admin_list_routes')
