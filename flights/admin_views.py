from django.conf import settings
from django.views.generic import View, DetailView, FormView, UpdateView, TemplateView, ListView, CreateView, DeleteView, WeekArchiveView, MonthArchiveView, \
    RedirectView
from django.views.generic.detail import SingleObjectMixin
from django.views.generic.edit import FormMixin
from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from django.core.urlresolvers import reverse, reverse_lazy
from django.http import Http404, HttpResponseRedirect
from django.utils.functional import cached_property
from django.http import HttpResponse
from django.db import transaction
from django.db.models import Q, F, Sum
from django.core.exceptions import ValidationError
from billing.models import  Card, BankAccount,BillingPaymentMethod
from billing import paymentMethodUtil
from formtools.wizard.views import SessionWizardView
from announcements.models import AutomatedMessage
from auditlog.models import LogEntry
import arrow
from datetime import datetime, timedelta, time
import stripe
import json
import calendar
import unicodecsv
from collections import OrderedDict, defaultdict
from django.db.models import Count

from accounts.mixins import StaffRequiredMixin, PermissionRequiredMixin, PermissionRequiredAnyMixin
from accounts.models import User, UserProfile
from rise import util
from .admin_forms import AirportForm, PlaneForm, FlightForm, FlightSetStatusForm, RouteForm, RouteTimeForm, RouteListForm, FlightListFilterForm, FlightMessageForm

from .admin_forms import (
    CancelFlightForm, DelayedFlightForm, FlightBookMemberForm, FlightBookMemberConfirmForm, FlightBookMemberPayForm,
    FlightPlanSeatRestrictionFormSet, AnywhereFlightEditForm, AnywhereFlightBookMemberForm, AdminAnywhereFlightCreationForm
)
from .models import (
    Airport, Plane, Route, RouteTime, Flight, RouteTimePlanRestriction, FlightPlanRestriction, FlightMessage,FlightWaitlist,
    FlightPlanSeatRestriction,
    AnywhereFlightDetails)
from billing.models import Plan
from reservations.models import Passenger, FlightPassengerAuditTrail, FlightReservation, Reservation,ReservationError
from .tasks import send_marketing_flight_email
from anywhere.models import AnywhereFlightRequest, AnywhereRoute, AnywhereFlightSet

stripe.api_key = settings.STRIPE_API_KEY
import flights.admin

class AdminAirportDetailView(StaffRequiredMixin, PermissionRequiredMixin, DetailView):
    """
    Detail view for an airport
    """

    permission_required = 'accounts.can_edit_flights'
    template_name = 'flights/admin/airport_detail.html'
    model = Airport


class AdminAirportAuditView(StaffRequiredMixin, PermissionRequiredMixin, DetailView):
    """
    Detail view for an airport
    """

    permission_required = 'accounts.can_edit_flights'
    template_name = 'flights/admin/airport_audit.html'
    model = Airport

    def get_context_data(self, **kwargs):
        context = super(AdminAirportAuditView, self).get_context_data(**kwargs)

        logs = LogEntry.objects.get_for_object(self.object)

        context.update({
            'logs': logs,
        })
        return context


class AdminAirportListView(StaffRequiredMixin, PermissionRequiredMixin, ListView):
    """
    A view to list airports
    """

    permission_required = 'accounts.can_edit_flights'
    template_name = 'flights/admin/airport_list.html'
    model = Airport


class AdminCreateAirportView(StaffRequiredMixin, PermissionRequiredMixin, CreateView):
    """
    Admin view to add a :class:`flights.models.Airport`
    """

    permission_required = 'accounts.can_edit_flights'
    template_name = 'flights/admin/airport_form.html'
    form_class = AirportForm
    model = Airport
    success_url = reverse_lazy('admin_airports')


class AdminEditAirportView(StaffRequiredMixin, PermissionRequiredMixin, UpdateView):
    """
    Admin view to edit a :class:`flights.models.Airport`
    """

    permission_required = 'accounts.can_edit_flights'
    template_name = 'flights/admin/airport_form.html'
    form_class = AirportForm
    model = Airport
    success_url = reverse_lazy('admin_airports')


class AdminPlaneDetailView(StaffRequiredMixin, PermissionRequiredMixin, DetailView):
    """
    Detail view for planes
    """

    permission_required = 'accounts.can_edit_flights'
    template_name = 'flights/admin/plane_detail.html'
    model = Plane


class AdminPlaneAuditView(StaffRequiredMixin, PermissionRequiredMixin, DetailView):
    """
    Audit view for planes
    """

    permission_required = 'accounts.can_edit_flights'
    template_name = 'flights/admin/plane_audit.html'
    model = Plane

    def get_context_data(self, **kwargs):
        context = super(AdminPlaneAuditView, self).get_context_data(**kwargs)

        logs = LogEntry.objects.get_for_object(self.object)

        context.update({
            'logs': logs,
        })
        return context


class AdminPlaneDeleteView(StaffRequiredMixin, PermissionRequiredMixin, DeleteView):
    """
    A view to delete planes.

    Should be safe to delete a plan since the FKs should all revert back to null
    """

    permission_required = 'accounts.can_edit_flights'
    template_name = 'flights/admin/plane_confirm_delete.html'
    model = Plane
    success_url = reverse_lazy('admin_planes')


class AdminPlaneListView(StaffRequiredMixin, PermissionRequiredMixin, ListView):
    """
    Admin view to list all planes
    """

    permission_required = 'accounts.can_edit_flights'
    template_name = 'flights/admin/plane_list.html'
    model = Plane


class AdminCreatePlaneView(StaffRequiredMixin, PermissionRequiredMixin, CreateView):
    """
    Admin view to add a :class:`flights.models.Plane`
    """

    permission_required = 'accounts.can_edit_flights'
    template_name = 'flights/admin/plane_form.html'
    form_class = PlaneForm
    model = Plane
    success_url = reverse_lazy('admin_planes')


class AdminEditPlaneView(StaffRequiredMixin, PermissionRequiredMixin, UpdateView):
    """
    Admin view to edit a :class:`flights.models.Plane`
    """

    permission_required = 'accounts.can_edit_flights'
    template_name = 'flights/admin/plane_form.html'
    form_class = PlaneForm
    model = Plane
    success_url = reverse_lazy('admin_planes')


def show_anywhere_flight_return_form(wizard):
    """
    Tells the AdminCreateFlightView wizard whether to show the return trip form
    Args:
        wizard:

    Returns: True if this is a round trip, false if one-way

    """
    cleaned_data = wizard.get_cleaned_data_for_step('0') or {}
    if cleaned_data.get('total_legs') == 2:
        return True
    return False


class AdminNewAnywhereFlightSetView(FormView, StaffRequiredMixin, PermissionRequiredMixin):
    permission_required = 'accounts.can_edit_flights'
    template_name = "flights/admin/new_anywhere_flight.html"
    form_class = AdminAnywhereFlightCreationForm

    def get_initial(self):
        """
        Returns the initial data to use for forms on this view.
        """
        initial = super(AdminNewAnywhereFlightSetView, self).get_initial()
        initial['selected_seats'] = 0
        initial['total_legs'] = 1

        return initial

    def get_context_data(self, form, **kwargs):
        """
        had to add total_legs to context in addition to hidden form because the wizard template wasn't accessing it from
        the form properly for determining which buttons to render.
        Args:
            form:
            **kwargs:

        Returns:

        """
        context = super(AdminNewAnywhereFlightSetView, self).get_context_data(form=form, **kwargs)
        context.update({'total_legs': 1})
        return context

    def form_valid(self, form):
        current_user = self.request.user
        # first create a flight request from this.
        flightrequest = AnywhereFlightRequest()
        flightrequest.origin_city = form.cleaned_data["origin"]
        flightrequest.destination_city = form.cleaned_data["destination"]
        route = AnywhereRoute.objects.filter(origin_id=flightrequest.origin_city_id, destination_id=flightrequest.destination_city_id).first()
        flightrequest.outbound_route = route
        flightrequest.seats = form.cleaned_data["selected_seats"]
        flightrequest.seats_required = form.cleaned_data["seats_required"]
        flightrequest.depart_date = form.cleaned_data["start_date"]
        flightrequest.depart_when = AnywhereFlightRequest.WHEN_FLEXIBLE
        flight_creator = form.cleaned_data["flight_creator"]
        if flight_creator:
            flightrequest.created_by = flight_creator
        else:
            flightrequest.created_by = current_user
        flightrequest.status = AnywhereFlightRequest.STATUS_ACCEPTED
        flightrequest.sharing = form.cleaned_data["sharing"]
        flightrequest.is_round_trip = False
        flightrequest.save()

        # create flight
        flight = form.save(flightrequest, current_user)

        flightset = AnywhereFlightSet()

        #if created on behalf of another, book their seats after creating flightset
        if flight_creator:
            flightset.create(flightrequest, flight, None, flight_creator)

             # reserve the flight creator's seats
            flightset.reserve_creator_seats(flight_creator)
        else:
            flightset.create(flightrequest, flight, None, current_user)


        return redirect('admin_anywhere')



class AdminCreateAnywhereFlightSetView(SessionWizardView, StaffRequiredMixin, PermissionRequiredMixin):

    permission_required = 'accounts.can_edit_flights'
    template_name = "flights/admin/create_anywhere_flight.html"

    def get_form_initial(self, step):
        """
        Populates the initial form data based on the flight request, route etc.
        Args:
            step:

        Returns:

        """
        initial = self.initial_dict.get(step, {})
        flight_request = AnywhereFlightRequest.objects.filter(id=self.kwargs['pk']).first()
        if flight_request is None:
            return initial

        initial.update({
            'sharing': flight_request.sharing,
            'duration': util.duration_as_time(flight_request.duration),
            'full_flight_cost': flight_request.get_estimated_cost_for_leg(step),
            'seats_required': flight_request.seats_required
        })

        #populate total legs field so the conditional dictionary knows whether the wizard
        #will be showing one form or two.
        if flight_request.is_round_trip:
            initial.update({'total_legs': 2})
        else:
            initial.update({'total_legs': 1})

        initial.update({'selected_seats':flight_request.seats})

        route = AnywhereRoute.objects.filter(origin_id=flight_request.origin_city_id, destination_id=flight_request.destination_city_id).first()
        if route is None:
            route = AnywhereRoute.objects.filter(origin_id=flight_request.destination_city_id, destination=flight_request.origin_city_id).first()
        if route is not None:
            initial.update({'duration': route.duration_as_time()})

        #some of the fields are populated differently depending on step.
        if step == '0':
            #use origin --> destination / departure dates
            initial.update({
                'origin_city': flight_request.origin_city,
                'destination_city': flight_request.destination_city,
                'depart_date': flight_request.depart_date,
                'depart_when': flight_request.depart_when
            })
        else:
            #use destination --> origin / return dates
            initial.update({
                'origin_city': flight_request.destination_city,
                'destination_city': flight_request.origin_city,
                'depart_date': flight_request.return_date,
                'depart_when': flight_request.return_when
            })
        return initial

    def get_context_data(self, form, **kwargs):
        """
        had to add total_legs to context in addition to hidden form because the wizard template wasn't accessing it from
        the form properly for determining which buttons to render.
        Args:
            form:
            **kwargs:

        Returns:

        """
        context = super(AdminCreateAnywhereFlightSetView, self).get_context_data(form=form, **kwargs)
        flight_request = AnywhereFlightRequest.objects.filter(id=self.kwargs['pk']).first()
        if flight_request.is_round_trip:
            context.update({'total_legs': 2})
        else:
            context.update({'total_legs': 1})
        return context

    def done(self, form_list, **kwargs):
        """
        Creates Flights from the form data + some from initial request
        Then creates an AnywhereFlightSet and attaches those flights.
        Then creates Reservations for the flight creator based on how many seats they requested
        But these are not charged immediately.
        Then updates the status of the AnywhereFlightRequest.

        Args:
            form_list:
            **kwargs:

        Returns:

        """
        current_user = self.request.user
        flight_request = AnywhereFlightRequest.objects.filter(id=self.kwargs['pk']).first()
        if flight_request is None:
            raise ValidationError('Flight request not found')

        # save the individual flights
        outbound_form = form_list[0]
        outbound_flight = form_list[0].save(flight_request, current_user)
        return_flight = None
        if outbound_form.cleaned_data["total_legs"] == 2:
            return_form = form_list[1]
            return_flight = return_form.save(flight_request, current_user)

        # create the flightset
        flightset = AnywhereFlightSet()
        flightset.create(flight_request, outbound_flight, return_flight, current_user)

        # reserve the flight creator's seats
        flightset.reserve_creator_seats(current_user)

        flight_request.status = flight_request.STATUS_ACCEPTED
        flight_request.save()

        return redirect('admin_anywhere')

class AdminCreateFlightView(StaffRequiredMixin, PermissionRequiredMixin, FormView):
    """
    Admin view to add a :class:`flights.models.Flight`
    """

    permission_required = 'accounts.can_edit_flights'
    template_name = 'flights/admin/flight_edit.html'
    form_class = FlightForm

    def get_initial(self):
        """
        Returns the keyword arguments for instantiating the form.
        """
        initial = super(AdminCreateFlightView, self).get_initial()
        initial.update({'corporate_max': 4, 'companion_max': 4})
        return initial

    def get_success_url(self):
        return reverse_lazy('admin_dashboard')

    def get_context_data(self, *args, **kwargs):
        context = super(AdminCreateFlightView, self).get_context_data(*args, **kwargs)
        context.update({
            'flightplanseatrestrictions_formset': FlightPlanSeatRestrictionFormSet()
        })

        return context

    def get_flightplanseatrestrictions_formset_kwargs(self):
        kwargs = {}

        if self.request.method in ('POST', 'PUT'):
            kwargs.update({
                'data': self.request.POST,
                'files': self.request.FILES,
            })

        return kwargs

    def get_flightplanseatrestrictions_formset(self):
        form = FlightPlanSeatRestrictionFormSet(**self.get_flightplanseatrestrictions_formset_kwargs())
        return form

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        flightplanseatrestrictions_formset = self.get_flightplanseatrestrictions_formset()

        form_valid = form.is_valid()
        flightplanseatrestrictions_formset_valid = flightplanseatrestrictions_formset.is_valid()

        if all([form_valid, flightplanseatrestrictions_formset_valid]):
            return self.form_valid(form, flightplanseatrestrictions_formset)
        else:
            return self.form_invalid(form, flightplanseatrestrictions_formset)

    def form_invalid(self, form, flightplanseatrestrictions_formset):
        """
        If the form is invalid, re-render the context data with the
        data-filled form and errors.
        """
        return self.render_to_response(self.get_context_data(
            form=form, flightplanseatrestrictions_formset=flightplanseatrestrictions_formset))

    def form_valid(self, form, flightplanseatrestrictions_formset):
        flight = form.save_flight(created_by=self.request.user)
        self.object = flight
        flightplanseatrestrictions_formset.instance = self.object
        flightplanseatrestrictions_formset.save()

        messages.info(self.request, 'Created flight number "%s"' % self.object.flight_number)
        return HttpResponseRedirect(self.get_success_url())

class AdminEditAnywhereFlightView(StaffRequiredMixin, PermissionRequiredMixin, FormView):
    permission_required = 'accounts.can_edit_flights'
    template_name = 'flights/admin/edit_anywhere_flight.html'
    form_class = AnywhereFlightEditForm

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        context = self.get_context_data(object=self.object, form=form)
        return self.render_to_response(context)

    def get_object(self, **kwargs):
        flight_pk = self.kwargs.get('pk', None)
        return Flight.objects.select_related('route_time', 'plane').get(pk=flight_pk)

    def get_form_kwargs(self):
        """
        Returns the keyword arguments for instantiating the form.
        """
        kwargs = super(AdminEditAnywhereFlightView, self).get_form_kwargs()
        if hasattr(self, 'object'):
            kwargs.update({'instance': self.object})
        return kwargs

    def get_success_url(self):
        return reverse('admin_flight_detail', args=[self.kwargs.get('pk')])


    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form()
        form_valid = form.is_valid()

        if all([form_valid]):
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def form_valid(self, form):
        flight = self.get_object()

        flightset = AnywhereFlightSet.objects.filter(Q(leg1_id=flight.id) | Q(leg2_id=flight.id)).first()

        flight = form.save_flight(created_by=self.request.user, seats_to_confirm=flightset.seats_required)

        flightset.update_costs_after_admin_edit()


        self.object = flight

        if 'start_date' in form.changed_data or 'takeoff_time' in form.changed_data or 'duration' in form.changed_data:
            flight.send_intinerary_update(subject='Flight %s has been changed' % (flight.flight_number,))

        messages.info(self.request, 'Updated flight number "%s"' % self.object.flight_number)
        return HttpResponseRedirect(self.get_success_url())


class AdminEditFlightView(StaffRequiredMixin, PermissionRequiredMixin, FormView):
    """
    Admin view to add a :class:`flights.models.Flight`.  Behaves much like an UpdateView, except the form
    is not a ModelForm and it manages multiple models at once.
    """

    permission_required = 'accounts.can_edit_flights'
    template_name = 'flights/admin/flight_edit.html'
    form_class = FlightForm

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        context = self.get_context_data(object=self.object, form=form)
        return self.render_to_response(context)

    def get_object(self, **kwargs):
        flight_pk = self.kwargs.get('pk', None)
        return Flight.objects.select_related('route_time', 'plane').get(pk=flight_pk)

    def get_form_kwargs(self):
        """
        Returns the keyword arguments for instantiating the form.
        """
        kwargs = super(AdminEditFlightView, self).get_form_kwargs()
        if hasattr(self, 'object'):
            flight = self.object
            if flight.plane is None:
                route_time = flight.route_time
                if route_time is not None and route_time.plane is not None:
                    flight.plane = route_time.plane
                elif route_time is not None and route_time.route is not None and route_time.route.plane is not None:
                    flight.plane = route_time.route.plane
            kwargs.update({'instance': self.object})
        return kwargs

    def get_success_url(self):
        return reverse('admin_flight_detail', args=[self.kwargs.get('pk')])

    def get_context_data(self, *args, **kwargs):
        context = super(AdminEditFlightView, self).get_context_data(*args, **kwargs)

        if 'flightplanseatrestrictions_formset' not in context:
            seat_restrictions = FlightPlanSeatRestriction.objects.filter(flight=self.get_object())
            flightplanseatrestrictions_formset = FlightPlanSeatRestrictionFormSet(queryset=seat_restrictions, instance=self.get_object())

            context.update({
                'flightplanseatrestrictions_formset': flightplanseatrestrictions_formset
            })

        return context

    def get_flightplanseatrestrictions_formset_kwargs(self):
        kwargs = {
            'instance': self.object
        }
        if self.request.method in ('POST', 'PUT'):
            kwargs.update({
                'data': self.request.POST,
            })

        return kwargs

    def get_flightplanseatrestrictions_formset(self):
        form = FlightPlanSeatRestrictionFormSet(**self.get_flightplanseatrestrictions_formset_kwargs())
        return form

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form()
        flightplanseatrestrictions_formset = self.get_flightplanseatrestrictions_formset()

        form_valid = form.is_valid()
        flightplanseatrestrictions_formset_valid = flightplanseatrestrictions_formset.is_valid()

        if all([form_valid, flightplanseatrestrictions_formset_valid]):
            return self.form_valid(form, flightplanseatrestrictions_formset)
        else:
            return self.form_invalid(form, flightplanseatrestrictions_formset)

    def form_invalid(self, form, flightplanseatrestrictions_formset):
        """
        If the form is invalid, re-render the context data with the
        data-filled form and errors.
        """
        return self.render_to_response(self.get_context_data(
            form=form, flightplanseatrestrictions_formset=flightplanseatrestrictions_formset))

    def form_valid(self, form, flightplanseatrestrictions_formset):
        flight = form.save_flight(created_by=self.request.user)
        self.object = flight
        flightplanseatrestrictions_formset.save()

        if 'start_date' in form.changed_data or 'takeoff_time' in form.changed_data or 'duration' in form.changed_data:
            flight.send_intinerary_update(subject='Flight %s has been changed' % (flight.flight_number,))

        messages.info(self.request, 'Updated flight number "%s"' % self.object.flight_number)
        return HttpResponseRedirect(self.get_success_url())


class AdminFlightCancelView(StaffRequiredMixin, PermissionRequiredAnyMixin, SingleObjectMixin, FormView):
    """
    A form view for cancelling a flight and sending the flight cancel message
    """
    permission_required = ['accounts.can_update_flights', 'accounts.can_edit_flights_limited']
    template_name = 'flights/admin/flight_cancel.html'
    form_class = CancelFlightForm
    model = Flight

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super(AdminFlightCancelView, self).dispatch(request, *args, **kwargs)

    def get_initial(self):
        initial = super(AdminFlightCancelView, self).get_initial()

        flight = self.object
        # default message for confirmed anywhere flights should mention that charges are refunded.
        if flight.flight_type == Flight.TYPE_ANYWHERE and flight.anywhere_details.confirmation_status == AnywhereFlightDetails.CONFIRMATION_STATUS_CONFIRMED:
            flightset = AnywhereFlightSet.objects.filter(Q(leg1_id=flight.id) | Q(leg2_id=flight.id)).first()
            if flightset.leg1_id == flight.id:
                message = "Flight %s has been cancelled.  All charges have been refunded." % (flight.flight_number)
            else:
                message = 'Flight %s has been cancelled.' % (flight.flight_number)
        else:
            message = 'Flight %s has been cancelled.' % (flight.flight_number)


        initial.update({
            'message': message
        })
        return initial

    def get_context_data(self, **kwargs):
        context = super(AdminFlightCancelView, self).get_context_data(**kwargs)

        context.update({
            'flight': self.object,
        })

        return context

    def form_valid(self, form):
        flight = self.object
        flightset = None
        if flight.flight_type == Flight.TYPE_ANYWHERE:
            flightset = AnywhereFlightSet.objects.filter(Q(leg1_id=flight.id) | Q(leg2_id=flight.id)).first()

        #  need to send message before cancelling flight, otherwise there will be no passengers to send to.
        message = form.cleaned_data.get('message')

        flight_message = FlightMessage.objects.create(flight=flight, message=message, created_by=self.request.user)
        flight_message.send(flightset=flightset)

        refund_eligible=False
        if not flightset:
            msgs = flight.cancel(True) #these default to true even though most people won't have fees.
        else:
            refund_eligible = flightset.is_refund_eligible(flight.id) #see below comment for why might not be eligible
            msgs = flight.cancel(refund_eligible)


        # if this is an anywhere flight they need to cancel both flights, tell them if they haven't already cancelled the other.
        # unless they are cancelling 2nd leg and first has already gone.
        # In that scenario there is no refund because all cost is frontloaded.

        if flightset is not None:
            if flight.anywhere_details.anywhere_request.is_round_trip:

                if flightset.leg1_id==self.object.id:
                    other = flightset.leg2
                    cancelled_leg1 = True
                else:
                    other = flightset.leg1
                    cancelled_leg1 = False
                if other.status != Flight.STATUS_CANCELLED and other.status != Flight.STATUS_COMPLETE:
                    # if we are cancelling leg1, leg2 must also get cancelled.
                    if flight == flightset.leg1:
                        messages.success(self.request, "Flight " + flight.flight_number + " has been cancelled.  "
                                                                                      "However, the return leg of this Rise Anywhere flightset, Flight "
                                     + other.flight_number + ", must also be cancelled.  Flight " + other.flight_number + " has been loaded for you. " + msgs)
                        return redirect('admin_flight_detail', other.pk)
                    # if we are cancelling leg 2, and leg 1 is not complete or cancelled we don't have to do anything necessarily.
                    # however if we were not refund eligible, and they do later cancel leg 1 we could have a problem if only leg 1's cost is refunded.
                    messages.success(self.request, "Flight " + flight.flight_number + " has been cancelled.  The outbound flight for this"
                                                                                      "flightset has not been cancelled. " + msgs)
                elif other.status == Flight.STATUS_COMPLETE:
                    # don't need to cancel the other leg, but set flightset to partlycancelled.
                    flightset.confirmation_status = AnywhereFlightSet.CONFIRMATION_STATUS_PARTLYCANCELLED
                    messages.success(self.request, "Flight " + flight.flight_number + " has been cancelled.  Charges for this leg of the Anywhere Flight cannot be refunded "
                                                                                      "since the other leg of this Rise Anywhere flightset, Flight "
                                     + other.flight_number + ", has already completed. " + msgs)
                else:
                    # if we cancelled leg1 just now and leg2 had been cancelled before,
                    # then it needs to get refunded now.
                    if cancelled_leg1:
                        msgs = other.refund_previously_cancelled_reservations()

                    # need to cancel the flightset as well
                    flightset.confirmation_status = AnywhereFlightSet.CONFIRMATION_STATUS_CANCELLED
                    flightset.save()

                    messages.success(self.request, "Flight " + flight.flight_number + " has been cancelled. %s" % msgs)
            else:
                # need to cancel the flightset as well
                flightset.confirmation_status = AnywhereFlightSet.CONFIRMATION_STATUS_CANCELLED
                flightset.save()
                messages.success(self.request, "Flight " + flight.flight_number + " has been cancelled.")

        return redirect('admin_flight_detail', flight.pk)


class AdminFlightMarketingView(StaffRequiredMixin, PermissionRequiredMixin, View):
    """
    View to send marketing email
    """

    permission_required = 'accounts.can_update_flights'

    def get(self, request, *args, **kwargs):
        flight_id = self.kwargs.get('pk')
        send_marketing_flight_email.delay(flight_id)

        FlightMessage.objects.create(flight_id=flight_id, message='Marketing Email Sent', created_by=request.user, internal=True)

        messages.info(request, 'Marketing Email Sent')

        return redirect('admin_flight_detail', flight_id)


class AdminFlightDeleteView(StaffRequiredMixin, PermissionRequiredMixin, DeleteView):
    """
    A form view for deleting a canceled flight
    """
    permission_required = 'accounts.can_update_flights'
    template_name = 'flights/admin/flight_delete.html'
    model = Flight
    context_object_name = "flight"
    success_url = reverse_lazy('admin_list_flights')

    def dispatch(self, request, *args, **kwargs):
        flight = self.get_object()
        if not flight.is_cancelled():
            messages.error(request, 'Flight must be canceled first to be deleted.')
            return redirect('admin_flight_cancel', flight.pk)
        else:
            return super(AdminFlightDeleteView, self).dispatch(request, *args, **kwargs)

    def post(self, *args, **kwargs):
        response = super(AdminFlightDeleteView, self).post(self, *args, **kwargs)
        messages.info(self.request, 'Flight has been deleted successfully.')
        return response


class AdminFlightDelayedView(StaffRequiredMixin, PermissionRequiredAnyMixin, SingleObjectMixin, FormView):
    """
    A form view for cancelling a flight and sending the flight cancel message
    """

    permission_required = ['accounts.can_update_flights', 'accounts.can_edit_flights_limited']
    template_name = 'flights/admin/flight_delay.html'
    form_class = DelayedFlightForm
    model = Flight

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super(AdminFlightDelayedView, self).dispatch(request, *args, **kwargs)

    def get_initial(self):
        initial = super(AdminFlightDelayedView, self).get_initial()

        flight = self.object

        automated_message = AutomatedMessage.objects.filter(message_key=AutomatedMessage.FLIGHT_DELAY_NOTIFICATION).first()
        message = automated_message.message_box_text
        if message is not None:
            message = message.replace("[[flight]]",flight.flight_number)
        else:
            message = 'Flight %s has been delayed.' % (flight.flight_number,)
        initial.update({
            'message': message,
            'departure_time': flight.departure,
            'departure_date': flight.departure,
        })
        return initial

    def get_context_data(self, **kwargs):
        context = super(AdminFlightDelayedView, self).get_context_data(**kwargs)

        context.update({
            'flight': self.object,
        })

        return context

    def form_valid(self, form):
        flight = self.get_object()

        # get the indvidual date/times
        departure_date = form.cleaned_data.get('departure_date')
        departure_time = form.cleaned_data.get('departure_time')

        # combine them together and apply the origin timezone
        new_departure = arrow.get(datetime.combine(departure_date, departure_time), flight.origin.timezone).datetime

        # delay the flight
        flight.delay(new_departure)

        # send the message
        subject = 'Flight %s has been delayed' % (flight.flight_number,)
        title = subject
        message = form.cleaned_data.get('message')
        flight_message = FlightMessage.objects.create(flight=flight, message=message, created_by=self.request.user)
        flight_message.send(sms_only=True)

        flight.send_intinerary_update(subject=subject, message=message, title=title)

        return redirect('admin_flight_detail', flight.pk)


class AdminFlightWeekView(StaffRequiredMixin, PermissionRequiredMixin, WeekArchiveView):
    """
    Display a list of flights for a given week
    """

    permission_required = 'accounts.can_view_flights'
    allow_empty = True
    allow_future = True
    model = Flight
    date_field = 'departure'
    template_name = 'flights/admin/flight_list_week.html'

    def get_queryset(self):
        queryset = super(AdminFlightWeekView, self).get_queryset()
        status_list=[Flight.STATUS_ON_TIME,Flight.STATUS_DELAYED,Flight.STATUS_IN_FLIGHT,Flight.STATUS_COMPLETE,Flight.STATUS_CANCELLED]
        queryset = queryset.filter(status__in=status_list)
        queryset = queryset.order_by('departure')
        return queryset

    def get_context_data(self, **kwargs):
        context = super(AdminFlightWeekView, self).get_context_data(**kwargs)
        flight_query_set = context.get('object_list')
        idlist = flight_query_set.values_list('id',flat=True)
        flightwaitlist = FlightWaitlist.objects.filter(flight_id__in=idlist,status=FlightWaitlist.STATUS_WAITING).\
            values('flight_id').annotate(Count('id')).order_by()
        waitlistdict={}
        for key in flightwaitlist:
            waitlistdict[key.get('flight_id')]=key.get('id__count')
        context.update({
            'now': arrow.now(),
            'waitlist':waitlistdict,

        })

        return context


class AdminFlightMonthView(StaffRequiredMixin, PermissionRequiredMixin, MonthArchiveView):
    """
    Display a list of flights for a given week
    """

    permission_required = 'accounts.can_view_flights'
    allow_empty = True
    allow_future = True
    model = Flight
    date_field = 'departure'
    template_name = 'flights/admin/flight_list_month.html'
    month_format = '%m'

    def get_queryset(self):
        queryset = super(AdminFlightMonthView, self).get_queryset()
        status_list=[Flight.STATUS_ON_TIME,Flight.STATUS_DELAYED,Flight.STATUS_IN_FLIGHT,Flight.STATUS_COMPLETE,Flight.STATUS_CANCELLED]
        queryset = queryset.filter(status__in=status_list)
        queryset = queryset.order_by('departure')
        return queryset

    def get_context_data(self, **kwargs):
        context = super(AdminFlightMonthView, self).get_context_data(**kwargs)
        flight_query_set = context.get('object_list')
        idlist = flight_query_set.values_list('id',flat=True)
        flightwaitlist = FlightWaitlist.objects.filter(flight_id__in=idlist,status=FlightWaitlist.STATUS_WAITING).\
            values('flight_id').annotate(Count('id')).order_by()
        waitlistdict={}
        for key in flightwaitlist:
            waitlistdict[key.get('flight_id')]=key.get('id__count')
        context.update({
            'now': arrow.now(),
            'waitlist':waitlistdict,

        })
        return context


class AdminFlightListView(StaffRequiredMixin, PermissionRequiredMixin, FormMixin, ListView):
    """
    Admin Flight list
    """

    permission_required = 'accounts.can_view_flights'
    model = Flight
    template_name = 'flights/admin/flight_list.html'
    form_class = FlightListFilterForm

    def get_context_data(self, **kwargs):
        context = super(AdminFlightListView, self).get_context_data(**kwargs)

        now = arrow.now()
        is_today = False
        flight_date = None
        if len(self.request.GET) == 0:
            # default queryset is for current day
            is_today = True
        else:
            date = self.request.GET.get('date', None)
            try:
                flight_date = arrow.get('%sT00:00:00%s' % (date, now.format('ZZ'))).floor('day')
                if date is not None and flight_date == now.floor('day'):
                    is_today = True
            except:
                date = None
        flight_query_set = context.get('object_list')
        idlist = flight_query_set.values_list('id',flat=True)
        flightwaitlist = FlightWaitlist.objects.filter(flight_id__in=idlist,status=FlightWaitlist.STATUS_WAITING).\
            values('flight_id').annotate(Count('id')).order_by()
        waitlistdict={}
        for key in flightwaitlist:
            waitlistdict[key.get('flight_id')]=key.get('id__count')
        context.update({
            'form': self.get_form(self.form_class),
            'now': now,
            'is_today': is_today,
            'flight_date': flight_date,
            'waitlist':waitlistdict,
        })

        return context

    def get_form_kwargs(self):
        """
        Returns the keyword arguments for instantiating the form.

        Sets up appropriate choices for date selection based on days which have flights scheduled.
        """

        queryset = super(AdminFlightListView, self).get_queryset()
        status_list=[Flight.STATUS_ON_TIME,Flight.STATUS_DELAYED,Flight.STATUS_IN_FLIGHT,Flight.STATUS_COMPLETE,Flight.STATUS_CANCELLED]
        queryset = queryset.filter(status__in=status_list)
        today = arrow.now().floor('day').datetime

        datetimes = queryset.filter(departure__gte=today).values_list('departure', flat=True).order_by('departure')

        dates = list(OrderedDict.fromkeys([arrow.get(datetime).to('local').date() for datetime in datetimes]))
        # dates = set([arrow.get(datetime).to('local').date() for datetime in datetimes])

        dates = [(date.strftime("%Y-%m-%d"), date.strftime("%A, %B %d")) for date in dates]

        kwargs = {
            'initial': self.get_initial(),
            'prefix': self.get_prefix(),
            'data': self.request.GET,
            'date_choices': dates,
        }

        return kwargs

    def get_queryset(self):
        """
        Applies filtering to the flight queryset based on GET parameters handled by FlightListFilterForm
        """
        queryset = super(AdminFlightListView, self).get_queryset()
        queryset = queryset.select_related('plane', 'origin', 'destination', 'route_time', 'pilot')
        s = self.request.GET.get('s', None)

        form = self.get_form(self.form_class)
        form.is_valid()
        flight_type_filter = form.cleaned_data.get('type', '')
        if not flight_type_filter:
            form.initial['type'] = ''

        flight_args = {}

        if flight_type_filter == FlightListFilterForm.TypeChoices.PROMO:
            flight_args['flight_type'] = Flight.TYPE_PROMOTION
        if flight_type_filter == FlightListFilterForm.TypeChoices.FUN:
            flight_args['flight_type'] = Flight.TYPE_FUN

        # flight_type_filter overrides date parameter
        flight_date = form.cleaned_data.get('date')
        if flight_date is None:
            start = arrow.now().floor('day')
        else:
            start = arrow.get(flight_date, 'local')

        end = start.replace(hours=24)

        flight_args['departure__gte'] = start.datetime
        flight_args['departure__lte'] = end.datetime

        queryset = queryset.filter(**flight_args)

        if s:
            queryset = queryset.filter(
                Q(flight_number__icontains=s) |
                Q(origin__name__icontains=s) |
                Q(origin__code__icontains=s) |
                Q(destination__name__icontains=s) |
                Q(destination__code__icontains=s)
            )

        queryset = queryset.order_by('departure')

        return queryset


class AdminFlightListBackgroundCheckView(StaffRequiredMixin, PermissionRequiredMixin, FormMixin, ListView):
    """
    Admin Flight list of users and their background check status
    """

    model = Flight
    template_name = 'flights/admin/background_check_list.html'
    form_class = FlightListFilterForm
    permission_required = 'accounts.can_background_check'

    def get_context_data(self, **kwargs):
        context = super(AdminFlightListBackgroundCheckView, self).get_context_data(**kwargs)

        now = arrow.now()
        is_today = False
        flight_date = None
        if len(self.request.GET) == 0:
            # default queryset is for current day
            is_today = True
        else:
            date = self.request.GET.get('date', None)
            try:
                flight_date = arrow.get('%sT00:00:00%s' % (date, now.format('ZZ'))).floor('day')
                if date is not None and flight_date == now.floor('day'):
                    is_today = True
            except:
                date = None

        context.update({
            'form': self.get_form(self.form_class),
            'now': now,
            'is_today': is_today,
            'flight_date': flight_date,
        })

        return context

    def get_form_kwargs(self):
        """
        Returns the keyword arguments for instantiating the form.

        Sets up appropriate choices for date selection based on days which have flights scheduled.
        """

        queryset = super(AdminFlightListBackgroundCheckView, self).get_queryset()
        today = arrow.now().floor('day').datetime

        datetimes = queryset.filter(departure__gte=today).values_list('departure', flat=True).order_by('departure')

        dates = list(OrderedDict.fromkeys([arrow.get(datetime).to('local').date() for datetime in datetimes]))

        dates = [(date.strftime("%Y-%m-%d"), date.strftime("%A, %B %d")) for date in dates]

        kwargs = {
            'initial': self.get_initial(),
            'prefix': self.get_prefix(),
            'data': self.request.GET,
            'date_choices': dates,
        }

        return kwargs

    def get_queryset(self):
        """
        Applies filtering to the flight queryset based on GET parameters handled by FlightListFilterForm
        """
        queryset = super(AdminFlightListBackgroundCheckView, self).get_queryset()
        queryset = queryset.select_related('plane', 'origin', 'destination', 'route_time', 'pilot')
        s = self.request.GET.get('s', None)

        form = self.get_form(self.form_class)
        form.is_valid()
        flight_type_filter = form.cleaned_data.get('type', '')
        if not flight_type_filter:
            form.initial['type'] = ''

        flight_args = {}

        if flight_type_filter == FlightListFilterForm.TypeChoices.PROMO:
            flight_args['flight_type'] = Flight.TYPE_PROMOTION
        if flight_type_filter == FlightListFilterForm.TypeChoices.FUN:
            flight_args['flight_type'] = Flight.TYPE_FUN

        # flight_type_filter overrides date parameter
        flight_date = form.cleaned_data.get('date')
        if flight_date is None:
            start = arrow.now().floor('day')
        else:
            start = arrow.get(flight_date, 'local')

        end = start.replace(hours=24)

        flight_args['departure__gte'] = start.datetime
        flight_args['departure__lte'] = end.datetime

        queryset = queryset.filter(**flight_args)

        if s:
            queryset = queryset.filter(
                Q(flight_number__icontains=s) |
                Q(origin__name__icontains=s) |
                Q(origin__code__icontains=s) |
                Q(destination__name__icontains=s) |
                Q(destination__code__icontains=s)
            )

        queryset = queryset.order_by('departure')

        return queryset


class UpdateBackgroundCheckStatusView(StaffRequiredMixin, PermissionRequiredMixin, View):
    """
    Ajax view to update given passenger's background check status
    """

    permission_required = 'accounts.can_background_check'

    def post(self, request, *args, **kwargs):
        flight_pk = self.kwargs.get('flight_pk', None)
        passenger_pk = self.kwargs.get('passenger_pk', None)
        background_status = request.POST.get('background_status', None)
        if flight_pk and passenger_pk and background_status.isdigit() and int(background_status) in [Passenger.BACKGROUND_NOT_STARTED, Passenger.BACKGROUND_PASSED]:
            flight_obj = get_object_or_404(Flight, pk=flight_pk)
            passenger_obj = get_object_or_404(Passenger, pk=passenger_pk)
            passenger_obj.background_status = background_status
            passenger_obj.save()

            FlightPassengerAuditTrail.objects.create(
                passenger=passenger_obj,
                passenger_first_name=passenger_obj.first_name,
                passenger_last_name=passenger_obj.last_name,
                passenger_date_of_birth=passenger_obj.date_of_birth,
                flight=flight_obj,
                created_by=request.user,
                update_type=FlightPassengerAuditTrail.UPDATE_BACKGROUND_CHECK_STATUS,
                update_details="Updated background check status for flight to %s" % background_status)

            json_response = {'success': 'True'}
        else:
            json_response = {'error': "There was an error updating the Passenger %s." % passenger_pk}

        return HttpResponse(json.dumps(json_response),
            content_type='application/json')


class AdminFlightAuditView(StaffRequiredMixin, PermissionRequiredMixin, DetailView):
    """
    Admin Flight audit view
    """

    permission_required = 'accounts.can_view_flights'
    template_name = 'flights/admin/flight_audit.html'
    model = Flight

    def get_context_data(self, **kwargs):
        context = super(AdminFlightAuditView, self).get_context_data(**kwargs)

        logs = LogEntry.objects.get_for_object(self.object)

        context.update({
            'logs': logs,
        })
        return context

class AdminFlightAnywhereReservationsView(StaffRequiredMixin, TemplateView):
    permission_required = 'accounts.can_view_flights'
    template_name = 'flights/admin/anywhere_flight_reservations_view.html'

    def get_context_data(self, **kwargs):
        context = super(AdminFlightAnywhereReservationsView, self).get_context_data(**kwargs)
        flight_pk = self.kwargs.get('pk', None)
        flight = Flight.objects.filter(id=flight_pk).first()
        context["flight"] = flight
        flightset = AnywhereFlightSet.objects.filter(Q(leg1_id=flight_pk) | Q(leg2_id=flight_pk)).first()
        context["flightset"] = flightset
        reservation_ids = flight.get_anywhere_reservations().values_list('reservation', flat=True)
        needs_charge = Reservation.objects.filter(id__in=reservation_ids, charge__isnull=True).count()
        context["num_uncharged_reservations"] = needs_charge
        needs_refund = flight.get_anywhere_reservations().filter(anywhere_refund_due__gt=0, anywhere_refund_paid=False).count()
        context["num_unrefunded_reservations"] = needs_refund
        return context

class AdminFlightDetailView(StaffRequiredMixin, UpdateView):
    """
    Admin flight detail
    """

    permission_required = 'accounts.can_view_flights'
    template_name = 'flights/admin/flight_detail.html'
    form_class = FlightSetStatusForm
    model = Flight

    def get_success_url(self):
        return reverse_lazy()

    def get_context_data(self, **kwargs):
        #If this is an Anywhere flight, even if the flight is full (aka all seats sold), there
        #is a possibility that we haven't captured the names of all the passengers
        #on the flight creator's reservation yet, in which case we will still need to show
        #the "add passengers" button.
        context = super(AdminFlightDetailView, self).get_context_data(**kwargs)
        flight = self.object
        if flight.flight_type == 'A':
            flightset = AnywhereFlightSet.objects.filter(Q(leg1_id=flight.id) | Q(leg2_id=flight.id)).first()
            context["flightset"] = flightset
        needs_creator_reservation_names = False
        if flight.flight_type == Flight.TYPE_ANYWHERE:
            creator = flight.anywhere_details.flight_creator_user
            #get the flight reservation for this flight that belongs to the creator
            if creator.account:
                flightres = FlightReservation.objects.filter(flight_id=flight.id, reservation__account_id=creator.account.id).first()

                if flightres is not None:
                     named_passenger_count = Passenger.objects.filter(flight_reservation_id=flightres.id).count()
                     if flightres.passenger_count > named_passenger_count:
                         needs_creator_reservation_names = True

        context["needs_creator_reservation_names"] = needs_creator_reservation_names
        return context


    def get_form_kwargs(self):
        kwargs = super(AdminFlightDetailView, self).get_form_kwargs()

        kwargs.update({
            'user': self.request.user,
        })

        return kwargs

    def form_valid(self, form):
        flight = self.object = form.save()
        status = flight.status

        user = self.request.user

        if user.has_perm('accounts.can_edit_flights') or user.has_perm('accounts.can_update_flights') or user.has_perm('accounts.can_edit_flights_limited'):
            if status == Flight.STATUS_CANCELLED:
                return redirect('admin_flight_cancel', flight.pk)

            elif status == Flight.STATUS_DELAYED:
                return redirect('admin_flight_delay', flight.pk)

            elif status == Flight.STATUS_IN_FLIGHT:
                flight.in_flight()

            elif status == Flight.STATUS_COMPLETE:
                flightset=None
                if flight.flight_type == Flight.TYPE_ANYWHERE:
                    flightset = AnywhereFlightSet.objects.filter(Q(leg1_id=flight.id) | Q(leg2_id=flight.id)).first()
                try:
                    flight.complete(flightset, self.request.user)
                except ReservationError as e:
                    messages.error(self.request, e.message )
            if status == Flight.STATUS_CANCELLED and flight.get_passengers().exists():
                messages.info(self.request, 'Flight cancelled. Please send a message to reservation holders for this flight.')
                return redirect('admin_flight_message', flight.pk)
            else:
                return redirect('admin_flight_detail', flight.pk)

        else:
            messages.info(self.request, 'Your account does not have authorization to edit flight status. Please contact support@iflyrise.com if you need assistance.')

        return redirect('admin_flight_detail', flight.pk)

class AdminAnywhereFlightBookMemberView(StaffRequiredMixin, PermissionRequiredMixin, FormView):
    """
    Allows a rise admin to book a member on a flight
    """
    permission_required = 'accounts.can_book_members'
    template_name = 'flights/admin/anywhere_flight_book_member.html'
    form_class = AnywhereFlightBookMemberForm

    def get_context_data(self, **kwargs):
        context = super(AdminAnywhereFlightBookMemberView, self).get_context_data(**kwargs)
        full = self.request.GET['full']
        if full == "True":
            full = True
        else:
            full = False
        flight_id = self.kwargs.get('pk', None)
        flightset = AnywhereFlightSet.objects.filter(leg1_id=flight_id).first()
        if flightset is None:
            flightset = AnywhereFlightSet.objects.filter(leg2_id=flight_id).first()
        creator = flightset.flight_creator_user
        flightres = None
        if creator.account:
            flightres = FlightReservation.objects.filter(flight_id=flight_id, reservation__account_id=creator.account.id).first()
            if flightres is not None:
                #there is a creator reservation to potentially tack onto.
                if flightres.passenger_count > 1:
                    #see how many passengers already are added
                    passenger_count = Passenger.objects.filter(flight_reservation_id=flightres.id).count()
                    if flightres.passenger_count > passenger_count:
                        #there is room for this user to be added on the creator's reservation if desired.
                        context.update({
                            'creator_reservation': flightres.reservation,
                            'creator': creator,
                            'flight_full': full
                        })
        context['flightset_pk']=flightset.id
        if flightres is None:
            #see if there are seats left since this won't go on creator's reservation
            flight = Flight.objects.filter(id=flight_id).first()
            if flight is not None:
                if flight.seats_available < 1:
                    messages.error(self.request, "There are no seats available on these flights." )
                    return redirect(reverse_lazy('admin_flight_detail',kwargs={"pk": flight_id}))

        return context

    def form_valid(self, form):
        flight_pk = self.kwargs.get('pk', None)
        flight = get_object_or_404(Flight, pk=flight_pk)
        member = form.cleaned_data.get('member')
        add_to_existing_reservation = form.cleaned_data.get('add_to_existing_reservation')
        reservation_pk=0
        context = self.get_context_data()
        flightset_pk = context['flightset_pk']
        if add_to_existing_reservation:
            reservation_pk = context['creator_reservation'].id

        return redirect('admin_anywhere_flight_book_member_confirm', flightset_pk=flightset_pk, member_pk=member.pk, reservation_pk=reservation_pk)

class AdminAnywhereFlightBookMemberConfirmView(StaffRequiredMixin, PermissionRequiredMixin, TemplateView):
    permission_required = 'accounts.can_book_members'
    template_name = 'flights/admin/anywhere_flight_book_member_confirm.html'

    month_format = '%m'
    model = Airport

    def get_context_data(self, **kwargs):
        context = super(AdminAnywhereFlightBookMemberConfirmView,self).get_context_data(**kwargs)
        memberid = self.kwargs["member_pk"]
        member = UserProfile.objects.filter(id=memberid).first()
        flightsetid = self.kwargs["flightset_pk"]
        flightset = AnywhereFlightSet.objects.filter(id=flightsetid).first()
        reservationid = self.kwargs["reservation_pk"]
        reservation = None
        if reservationid > 0:
            reservation = Reservation.objects.filter(id=reservationid).first()
        context.update({
            'origin_airport': flightset.origin,
            'destination_airport': flightset.destination,
            'flightset': flightset,
            'member': member,
            'reservation': reservation
        })
        return context

    def post(self, request, *args, **kwargs):
        """
        Handles POST requests, instantiating a form instance with the passed
        POST variables and then checked for validity.
        """
        context = self.get_context_data()
        flightset = context["flightset"]
        if not flightset:
            messages.error(request, 'There was an error booking your requested flight.  Please try again or choose another flight.')
            return redirect(request.path)

        member = context["member"]
        if flightset.leg1.is_booked_by_user(member):
            messages.error(request, 'This person is already booked on this flight.')
            return redirect('admin_flight_detail', pk=flightset.leg1.id)

        reservation = None
        is_passenger_only = False
        try:
            if context["reservation"] is not None:
                is_passenger_only=True
                reservation = context["reservation"]
                # TODO when we open all reservtions up for multiple people, will need to figure out whose reservation it actually is.

                for flightres in reservation.flightreservation_set.all():
                    # these seats are already claimed on the creator's reservation
                    # so we don't need to deduct seat counts. we just create passenger record.
                    flightres.add_passenger(member)
                # send email to member & flight creator (only notify rise on 1st email)
                reservation.send_anywhere_reservation_email([member.email], "You've been added to a RISE ANYWHERE Reservation", member.get_full_name() + " has been added to a RISE ANYWHERE reservation belonging to " + flightset.flight_creator_user.get_full_name() + ".", "You've been added to a RISE ANYWHERE Reservation", False, True, flightset.flight_creator_user.get_full_name(), member.get_full_name() )
                reservation.send_anywhere_reservation_email([flightset.flight_creator_user.email], "Passenger Added to Rise Reservation", member.get_full_name() + " has been added to your existing reservation.", "Passenger Added to Rise Reservation")
            else:
                # create a new reservation, this WILL deduct seats from the flight(s).
                # this automatically sends email as well so don't need to do it here.
                reservation = flightset.reserve_seats(context["member"], 1, self.request.user)

            # if this flight has already been confirmed, we need to confirm this user's reservation & bill unless
            # we were just adding a passenger to an existing reservation.

            if reservation and flightset.confirmation_status == AnywhereFlightSet.CONFIRMATION_STATUS_CONFIRMED and not is_passenger_only:
                flightset.complete_reservations(self.request.user)
        except Exception as e:
            messages.error(self.request,e.message)

        if reservation is not None:
            if is_passenger_only:
                messages.success(request, "Passenger added to reservation successfully.")
            else:
                messages.success(request, "Reservation created successfully.")
            return redirect('admin_flight_detail', pk=flightset.leg1.id)

        messages.error(request, 'There was an error booking your requested flight. Please try again or choose another flight.')
        return redirect('admin_flight_detail', pk=flightset.leg1.id)


class AdminFlightBookMemberView(StaffRequiredMixin, PermissionRequiredMixin, FormView):
    """
    Allows a rise admin to book a member on a flight
    """
    permission_required = 'accounts.can_book_members'
    template_name = 'flights/admin/flight_book_member.html'
    form_class = FlightBookMemberForm

    def form_valid(self, form):
        flight_pk = self.kwargs.get('pk', None)
        flight = get_object_or_404(Flight, pk=flight_pk)
        member = form.cleaned_data.get('member')

        return redirect('admin_flight_book_member_confirm', pk=flight.pk, member_pk=member.pk)


class AdminFlightBookMemberConfirmView(StaffRequiredMixin, PermissionRequiredMixin, FormView):
    """
    Confirms booking of member and allows the adding of members/companions to the FlightReservation
    """
    permission_required = 'accounts.can_book_members'
    template_name = 'flights/admin/flight_book_member_confirm.html'
    form_class = FlightBookMemberConfirmForm

    def get_context_data(self, **kwargs):
        context = super(AdminFlightBookMemberConfirmView, self).get_context_data(**kwargs)

        context.update({
            'member': self.member,
            'flight': self.flight,
        })

        return context

    @cached_property
    def member(self):
        member_pk = self.kwargs.get('member_pk', None)
        member = get_object_or_404(UserProfile, pk=member_pk)

        return member

    @cached_property
    def flight(self):
        pk = self.kwargs.get('pk', None)
        flight = get_object_or_404(Flight, pk=pk)

        return flight

    def get_form_kwargs(self):
        kwargs = super(AdminFlightBookMemberConfirmView, self).get_form_kwargs()

        kwargs.update({
            'member': self.member,
        })

        return kwargs

    def form_valid(self, form):
        # these need to change to be user profiles!
        companions = form.cleaned_data.get('companions')

        #first figure out who is actually a member and who is a companion.

        primary_is_companion = False
        actual_member = None
        member_count=0
        companion_count = 0  #including primary

        if not self.member.user or not self.member.user.has_perm("accounts.can_book_flights"):
            #this is actually a companion
            primary_is_companion=True
            companion_count +=1
            # is a primary in the companion list?
            for comp in companions:
                # see which are members and which use passes
                if comp.user and comp.user.has_perm("accounts.can_book_flights"):
                    member_count += 1
                    # set the first actual member we find as primary
                    if not actual_member:
                        actual_member = comp
                else:
                    companion_count +=1
        else: # primary add is a member, this is the "old" flow
            actual_member = self.member
            member_count +=1
            # still have to see how many are companions and how many use passes
            for comp in companions:
                if comp.user and comp.user.has_perm("accounts.can_book_flights"):
                    member_count += 1
                else:
                    companion_count += 1

        passenger_count = member_count + companion_count

        if passenger_count > self.flight.seats_available:
            messages.error(self.request, "The number of seats for this reservation exceeds the seats available on the requested flight #%d." % self.flight.pk)
            return redirect('admin_flight_detail', self.flight.pk)

        noshow = self.member.active_noshow_restriction()
        if noshow:
            msg = AutomatedMessage.objects.filter(message_key=AutomatedMessage.NO_SHOW_RESTRICTION_ADMIN).first()
            if msg:
                msg_txt = msg.message_box_text.replace("[[end_date]]", noshow.end_date.strftime("%m-%d-%Y"))
                msg_txt = msg_txt.replace("[[FAQ_link]]", ("<a href='%s/faq' target='_blank'>here</a>" % settings.WP_URL))
                messages.error(self.request, msg_txt)
            else:
                messages.error(self.request, "This person is restricted from all RISE activity until %s due to excessive no-shows." % noshow.end_date)
            return redirect('admin_flight_book_member', self.flight.pk)

        # handling restrictions on Flight Reservations for this flight and member
        if not self.flight.check_account_restriction(self.member):
            messages.error(self.request, "There was an account restriction for %s on this flight. Please select a different member." % self.member.account)
            return redirect('admin_flight_book_member', self.flight.pk)

        if not self.flight.check_vip(self.member):
            messages.error(self.request, "There was a VIP restriction on this flight, and %s is not a VIP account. Please select a different member." % self.member.account)
            return redirect('admin_flight_book_member', self.flight.pk)

        if not self.flight.check_founder(self.member):
            messages.error(self.request, "There was a Founder restriction on this flight, and %s is not a Founder account. Please select a different member." % self.member.account)
            return redirect('admin_flight_book_member', self.flight.pk)

        if not self.flight.check_user_permissions(self.member, companion_count):
            messages.error(self.request, "There was a permission restriction for %s on this flight. Please select a different member." % self.member.get_full_name())
            return redirect('admin_flight_book_member', self.flight.pk)

        if not self.flight.check_plan_restrictions(self.member, companion_count):
            messages.error(self.request, "There was a plan restriction for %s on this flight. Please select a different member." % self.member.get_full_name())
            return redirect('admin_flight_book_member', self.flight.pk)

        if not self.flight.check_plan_seat_restrictions(self.member, (passenger_count)):
            messages.error(self.request, "There was a seat restriction for %s's plan on this flight. Please select a different member." % self.member.get_full_name())
            return redirect('admin_flight_book_member', self.flight.pk)

        if self.flight.is_booked_by_user(self.member):
            messages.error(self.request, "This flight already has a reservation for %s. Please select a different member." % self.member.get_full_name())
            return redirect('admin_flight_book_member', self.flight.pk)

        if actual_member:
            flight_reservation = self.flight.reserve_flight(self.request.user, actual_member, None, companion_count, False, member_count-1)
        else:
            flight_reservation = self.flight.reserve_flight(self.request.user, self.member, None, companion_count, True, member_count)

        if flight_reservation is not None:
            flight_reservation.clear_companions()
            if primary_is_companion:
                #AMF Rise-289 add the "first selected" companion first.  They will become the primary passenger.
                flight_reservation.add_passenger(self.member, companion=True)

            for companion in companions:
                # the 'actual member' already got added
                if not companion == actual_member:
                    if companion.account == self.member.account:
                        if companion.user and companion.user.has_perm("accounts.can_book_flights"):
                            flight_reservation.add_passenger(companion, companion=False)
                        else:
                            flight_reservation.add_passenger(companion, companion=True)

            flight_reservation.save()

            if flight_reservation.reservation.requires_payment():
                if (self.request.user.has_perm('accounts.can_charge_members')):
                    messages.info(self.request, 'Member must pay a surchange for Flight Reservation #%s.' % (flight_reservation.pk))
                    return redirect('admin_flight_book_member_pay', pk=flight_reservation.pk)
                else:
                    messages.error(self.request, 'Sorry. You need to be an Admin to change an account plan that incurs a surcharge.')
                    flight_reservation.cancel()
                    return redirect('admin_flight_detail', self.flight.pk)

            flight_reservation.reservation.reserve()
            messages.info(self.request, 'Flight Reservation #%s was successful.' % flight_reservation.pk)
        else:
            messages.error(self.request, 'There was an error booking the requested flight #%d for %s' % (self.flight.pk, self.member.get_full_name()))
            return redirect('admin_flight_detail', pk=self.flight.pk)

        return redirect('admin_flight_book_member_success', pk=flight_reservation.pk)

class AdminFlightAnywherePassengerCancelView(StaffRequiredMixin, PermissionRequiredMixin, View):
    """
    Removes a passenger from a flight creator's reservation w/o affecting the reservation itself
    """
    permission_required = 'accounts.can_book_members'

    def post(self, request, *args, **kwargs):
        form_values = request.POST

        pk = self.kwargs.get('pk', None)
        flight_reservation = get_object_or_404(FlightReservation, pk=pk)
        flight_id = flight_reservation.flight_id

        keepspots = form_values.get('keep_spots')

        passenger_id = self.kwargs.get('passenger_id', None)
        if passenger_id:
            userprofile = UserProfile.objects.filter(id=passenger_id).first()
            # wait to refund anywhere passengers until final cost reconciliation because they might have paid a different spot cost than current.
            # remove passenger will free the seats & update the actual reservation to have fewer spots
            # deleting the passenger object leaves the reservation w/ same # of spots
            if keepspots == "on":
                passenger = Passenger.objects.filter(flight_reservation_id=flight_reservation.id, userprofile_id=passenger_id).first()
                passenger.delete()
            else:
                flight_reservation.remove_passenger(userprofile, False)
            # see if there are other passenger records for this user from the Anywhere reservation
            flight_reservation.refresh_from_db()
            reservation = flight_reservation.reservation
            reservation.refresh_from_db()
            flight_reservations = reservation.flightreservation_set.filter(passenger__userprofile_id=userprofile.id).all()
            for fr in flight_reservations:
                if keepspots == "on":
                    passenger = Passenger.objects.filter(flight_reservation_id=fr.id, userprofile_id=userprofile.id).first()
                    passenger.delete()
                else:
                    fr.remove_passenger(userprofile, False)
                messages.success(self.request, "Passenger removed successfully from flight reservations %s and %s." % (pk, fr.id))
                return redirect('admin_flight_detail',pk=flight_id)

            messages.success(self.request, "Passenger removed successfully from flight reservation %s." % (pk))
            return redirect('admin_flight_detail',pk=flight_id)
        messages.error("Invalid request.")
        return redirect('admin_flight_detail',pk=flight_id)


class AdminFlightBookMemberCancelView(StaffRequiredMixin, PermissionRequiredMixin, View):
    """
    Cancels reservation for the passenger.  If this is only passenger on reservation, will cancel the whole thing.
    """
    permission_required = 'accounts.can_book_members'
    # def get(self, request, *args, **kwargs):
    #     pk = self.kwargs.get('pk', None)
    #     flight_reservation = get_object_or_404(FlightReservation, pk=pk)
    #     passengerid = self.kwargs.get('passenger_id', None)
    #     if passengerid:
    #         # see if there are other passengers.  if so, only drop the passenger, don't cancel the whole reservation.
    #
    #         if flight_reservation.passenger_count > 1:
    #             user = User.objects.filter(id=passengerid).first()
    #             flight_reservation.remove_passenger(user, True)
    #             message = '%s has been removed from Reservation %s' % (user.get_full_name(),pk)
    #             messages.info(request, message)
    #             return redirect('admin_flight_detail', pk=flight_reservation.flight.pk)
    #
    #     flight_reservation.cancel()
    #     # flight_reservation.save()
    #     message = 'Flight Reservation %s has been cancelled.' % pk
    #     if flight_reservation.flight.flight_type == Flight.TYPE_ANYWHERE:
    #         uncancelled = flight_reservation.reservation.flightreservation_set.exclude(status=FlightReservation.STATUS_CANCELLED).first()
    #         if uncancelled:
    #             #must also cancel the other reservation.
    #             uncancelled.cancel()
    #             message = "Flight Reservations %s and %s have been cancelled." % (pk, uncancelled.pk)
    #         #must also cancel the whole reservation
    #         flight_reservation.reservation.cancel(try_void_charge=True)
    #         messages.info(request, message)
    #     else:
    #         messages.info(request, message)
    #     return redirect('admin_flight_detail', pk=flight_reservation.flight.pk)

    def post(self, request, *args, **kwargs):
        form_values = request.POST
        pk = self.kwargs.get('pk', None)
        flight_reservation = get_object_or_404(FlightReservation, pk=pk)
        flight_reservation.cancellation_reason = form_values.get('cancellation_reason')
        passengerid = self.kwargs.get('passenger_id', None)
        if passengerid:
            # see if there are other passengers.  if so, only drop the passenger, don't cancel the whole reservation.
            if flight_reservation.passenger_count > 1:
                userprofile = UserProfile.objects.filter(id=passengerid).first()
                if flight_reservation.flight.flight_type == Flight.TYPE_ANYWHERE:
                    refund_eligible=False
                else:
                    refund_eligible=True
                flight_reservation.remove_passenger(userprofile, refund_eligible)
                message = '%s has been removed from Reservation %s' % (userprofile.get_full_name(),pk)
                messages.info(request, message)
                return redirect('admin_flight_detail', pk=flight_reservation.flight.pk)

        #only one passenger so cancel the reservation in toto.
        flight_reservation.cancel()
        # flight_reservation.save()
        message = 'Flight Reservation %s has been cancelled.' % pk
        if flight_reservation.flight.flight_type == Flight.TYPE_ANYWHERE:
            uncancelled = flight_reservation.reservation.flightreservation_set.exclude(status=FlightReservation.STATUS_CANCELLED).first()
            if uncancelled:
                #must also cancel the other reservation.
                uncancelled.cancellation_reason = form_values.get('cancellation_reason')
                uncancelled.cancel()
                message = "Flight Reservations %s and %s have been cancelled." % (pk, uncancelled.pk)
            #must also cancel the whole reservation
            flight_reservation.reservation.cancel(try_void_charge=True)
            messages.info(request, message)
        else:
            messages.info(request, message)
        return redirect('admin_flight_detail', pk=flight_reservation.flight.pk)



class AdminFlightBookMemberPayView(StaffRequiredMixin, PermissionRequiredMixin, FormView):
    """
    View when reservation requires additional payment from member's account
    """
    permission_required = 'accounts.can_charge_members'
    reservation_required = True
    template_name = 'flights/admin/flight_book_member_pay.html'
    form_class = FlightBookMemberPayForm

    def get_context_data(self, **kwargs):
        context = super(AdminFlightBookMemberPayView, self).get_context_data(**kwargs)

        flight_reservation = self.flight_reservation()

        account = flight_reservation.reservation.account
        bill_pay_methods = BillingPaymentMethod.objects.filter(account=account).all()
        cards = Card.objects.filter(account=account).all()
        bankaccounts = BankAccount.objects.filter(account=account,verified=True).all()
        paylist = []
        if cards is not None:
            for card in cards:
                paymethod = bill_pay_methods.filter(id=card.billing_payment_method_id).first()
                payment = {
                    "id":paymethod.id,
                    "is_default":paymethod.is_default,
                    "text":"Credit Card ending with " + card.last4,
                    "nickname":paymethod.nickname
                }
                paylist.append(payment)
        if bankaccounts is not None:
            for bankaccount in bankaccounts:
                paymethod = bill_pay_methods.filter(id=bankaccount.billing_payment_method_id).first()
                payment = {
                    "id":paymethod.id,
                    "is_default":paymethod.is_default,
                    "text":"Bank Account ending with " + bankaccount.last4,
                    "nickname":paymethod.nickname
                }
                paylist.append(payment)
        context.update({
            'flight_reservation': flight_reservation,
            'reservation': flight_reservation.reservation,
            'STRIPE_PUBLISHABLE_KEY': settings.STRIPE_PUBLISHABLE_KEY,
            'paylist': paylist,
        })

        return context

    def flight_reservation(self):
        pk = self.kwargs.get('pk', None)
        flight_reservation = get_object_or_404(FlightReservation, pk=pk)
        return flight_reservation

    def dispatch(self, request, *args, **kwargs):
        flight_reservation = self.flight_reservation()
        if flight_reservation.status == Reservation.STATUS_RESERVED:
            return redirect('admin_flight_book_member_success', pk=flight_reservation.pk)

        # credit_card = flight_reservation.reservation.account.get_credit_card()
        # if flight_reservation.reservation.account.is_credit_card and credit_card is None:
        #    messages.info(self.request, 'No card is on file for this account. Please override charge or add payment information.')

        # save the current path in case the admin user wants to return to this page
        pay_path = request.get_full_path()
        request.session['pay_path'] = pay_path

        return super(AdminFlightBookMemberPayView, self).dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        flight_reservation = self.flight_reservation()
        reservation = flight_reservation.reservation
        member = flight_reservation.primary_passenger.userprofile

        override_charge = int(form.cleaned_data.get('override_charge'))
        payment_method = self.request.POST.get('payment_method')
        if override_charge == 1:
            reservation.reserve()
            messages.info(self.request, 'Flight Reservation #%s was successful.' % flight_reservation.pk)
            return super(AdminFlightBookMemberPayView, self).form_valid(form)
        elif member.account.is_manual():
            messages.info(self.request, 'This account is manual. Please select "Override Charge" to continue.')
            return super(AdminFlightBookMemberPayView, self).form_invalid(form)
        elif payment_method is None:
            messages.info(self.request, 'No card is on file for this account. Please override charge or add payment information.')
            return super(AdminFlightBookMemberPayView, self).form_invalid(form)

        # if this reservation requires a payment
        if reservation.requires_payment():
            # get the amount to charge
            amount = reservation.total_amount()

            try:
                bill_pay_method = BillingPaymentMethod.objects.filter(id=payment_method).first()
                if bill_pay_method.payment_method == BillingPaymentMethod.PAYMENT_CREDIT_CARD:
                    # The payment selected is an existing credit card.
                    # The credit card transactions will go through braintree
                    card = Card.objects.filter(billing_payment_method=bill_pay_method).first()
                    charge = card.charge(amount, 'Charge for reservation on Flight %s' % flight_reservation.flight.pk, self.request.user)
                else:
                    # The payment selected is an existing bank account.
                    # The bank transactions will go through stripe
                    bankaccount = BankAccount.objects.filter(billing_payment_method=bill_pay_method).first()
                    charge = bankaccount.charge(amount, 'Charge for reservation on Flight %s' % flight_reservation.flight.pk, self.request.user)
            except Exception as e:
                messages.error(self.request, e.message)
                return self.form_invalid(form)
            if charge:
                with transaction.atomic():
                    reservation.charge = charge
                    reservation.save()
                    reservation.reserve()
                messages.info(self.request, 'Flight Reservation #%s was successful.' % flight_reservation.pk)
                return super(AdminFlightBookMemberPayView, self).form_valid(form)
            else:
                messages.error(self.request, 'There was an error charging the account.')
                return self.form_invalid(form)

        messages.info(self.request, 'Payment for Flight Reservation #%s has already been made.' % flight_reservation.pk)
        return redirect('admin_flight_book_member_success', pk=flight_reservation.pk)

    def get_success_url(self):
        flight_reservation = self.flight_reservation()
        return reverse('admin_flight_detail', args=[flight_reservation.flight.pk])


class AdminFlightBookMemberSuccessView(StaffRequiredMixin, PermissionRequiredMixin, DetailView):
    """
    View when reservation is successful
    """
    permission_required = 'accounts.can_book_members'
    template_name = 'flights/admin/flight_book_member_success.html'
    model = FlightReservation

    def dispatch(self, request, *args, **kwargs):
        flight_reservation = self.get_object()
        if flight_reservation.status != Reservation.STATUS_RESERVED:
            return redirect('admin_flight_book_member_pay', pk=flight_reservation.pk)

        return super(AdminFlightBookMemberSuccessView, self).dispatch(request, *args, **kwargs)


class AdminFlightPrintManifestView(StaffRequiredMixin, UpdateView):
    """
    Admin flight detail
    """

    permission_required = 'accounts.can_view_flights'
    template_name = 'flights/admin/flight_print_manifest.html'
    form_class = FlightSetStatusForm
    model = Flight

    def get_success_url(self):
        return reverse_lazy()

    def get_form_kwargs(self):
        kwargs = super(AdminFlightPrintManifestView, self).get_form_kwargs()

        kwargs.update({
            'user': self.request.user,
        })

        return kwargs

    def form_valid(self, form):
        self.object = flight = form.save()
        status = form.cleaned_data.get('status')

        if status == Flight.STATUS_CANCELLED:
            flight.cancel()

        elif status == Flight.STATUS_IN_FLIGHT:
            flight.in_flight()

        elif status == Flight.STATUS_COMPLETE:
            flight.complete()

        elif status == Flight.STATUS_DELAYED:
            pass

        return redirect('admin_flight_detail', flight.pk)


class AdminFlightBackgroundCheckView(StaffRequiredMixin, UpdateView):
    """
    Admin detail view for flight's passengers' background check statuses
    """

    permission_required = 'accounts.can_background_check'
    template_name = 'flights/admin/flight_background_check.html'
    form_class = FlightSetStatusForm
    model = Flight

    def get_form_kwargs(self):
        kwargs = super(AdminFlightBackgroundCheckView, self).get_form_kwargs()

        kwargs.update({
            'user': self.request.user,
        })

        return kwargs

    def form_valid(self, form):
        self.object = flight = form.save()
        status = form.cleaned_data.get('status')

        if status == Flight.STATUS_CANCELLED:
            flight.cancel()

        elif status == Flight.STATUS_IN_FLIGHT:
            flight.in_flight()

        elif status == Flight.STATUS_COMPLETE:
            flight.complete()

        elif status == Flight.STATUS_DELAYED:
            pass

        return redirect('admin_flight_detail', flight.pk)


class AdminRouteListView(StaffRequiredMixin, PermissionRequiredMixin, FormView):
    """
    Displays a list of routes, with the option to make a selection from these
    for automated flight creation
    """
    permission_required = 'accounts.can_edit_flights'
    model = Route
    template_name = 'flights/admin/route_list.html'
    form_class = RouteListForm
    success_url = reverse_lazy('admin_routes_select_flights')

    def get_context_data(self, **kwargs):
        context = super(AdminRouteListView, self).get_context_data(**kwargs)

        context.update({
            'route_list': Route.objects.all(),
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


class AdminRouteView(StaffRequiredMixin, PermissionRequiredMixin, DetailView):
    """
    View the details for the current flight
    """

    permission_required = 'accounts.can_edit_flights'
    template_name = 'flights/admin/route_detail.html'
    model = Route


class AdminCreateRouteView(StaffRequiredMixin, PermissionRequiredMixin, CreateView):
    """
    Admin view to add a :class:`flights.models.Flight`
    """

    permission_required = 'accounts.can_edit_flights'
    template_name = 'flights/admin/route_form.html'
    form_class = RouteForm
    model = Route

    def get_success_url(self):
        return reverse('admin_route_detail', args=[self.object.pk])


class AdminEditRouteView(StaffRequiredMixin, PermissionRequiredMixin, UpdateView):
    """
    Admin view to add a :class:`flights.models.Flight`
    """

    permission_required = 'accounts.can_edit_flights'
    template_name = 'flights/admin/route_form.html'
    form_class = RouteForm
    model = Route

    def get_success_url(self):
        return reverse('admin_route_detail', args=[self.object.pk])

    def form_valid(self, form):
        route = Route.objects.filter(id=self.object.id).first()
        old_plane_id = route.plane_id
        new_plane = form.cleaned_data.get('plane')
        if new_plane is not None and old_plane_id is not None and new_plane.id != old_plane_id:
            RouteTime.objects.filter(route=route,plane_id=old_plane_id).update(plane=new_plane)
            routeTime_list = RouteTime.objects.filter(route=route)
            Flight.objects.filter(route_time__in=routeTime_list,plane_id=old_plane_id).update(plane=new_plane)
        self.object = route = form.save()
        return redirect(self.get_success_url())

class AdminRouteDeleteView(StaffRequiredMixin, PermissionRequiredMixin, DeleteView):
    """
    Admin view to delete a route
    """
    permission_required = 'accounts.can_edit_flights'
    template_name = 'flights/admin/route_confirm_delete.html'
    model = Route
    success_url = reverse_lazy('admin_list_routes')

    def get(self, request, *args, **kwargs):
        route = Route.objects.filter(id=self.kwargs.get('pk', None))
        if route:
            route.delete()
        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse_lazy('admin_list_routes')


class AdminRouteTimeDeleteView(StaffRequiredMixin, PermissionRequiredMixin, DeleteView):
    """
    Admin view to delete a route
    """
    permission_required = 'accounts.can_edit_flights'
    template_name = 'flights/admin/routetime_confirm_delete.html'
    model = RouteTime

    def get_success_url(self):
        return reverse('admin_route_detail', args=[self.object.route_id])


class AdminCreateRouteTimeView(StaffRequiredMixin, PermissionRequiredMixin, CreateView):
    """
    Admin view to add a :class:`flights.models.RouteTime`
    """

    permission_required = 'accounts.can_edit_flights'
    template_name = 'flights/admin/routetime_form.html'
    form_class = RouteTimeForm
    model = RouteTime

    def get_success_url(self):
        return reverse_lazy('admin_route_detail', args=[self.route.pk])

    @cached_property
    def route(self, **kwargs):
        return Route.objects.get(pk=self.kwargs.get('route_pk'))

    def get_form_kwargs(self, **kwargs):
        kwargs = super(AdminCreateRouteTimeView, self).get_form_kwargs(**kwargs)
        route = self.route
        initial = kwargs.get('initial')
        initial.update({
            'plane': route.plane,
        })
        kwargs.update({
            'plans': Plan.objects.filter(active=True),
        })

        return kwargs

    def get_context_data(self, **kwargs):
        context = super(AdminCreateRouteTimeView, self).get_context_data(**kwargs)
        context.update({
            'route': self.route,
        })

        return context

    def form_valid(self, form):
        route_time = form.save(commit=False)

        route_time.route = self.route

        route_time.save()

        for plan, restriction_key, days_key in form.plan_fields_keys:
            checked = form.cleaned_data.get(restriction_key)
            days = form.cleaned_data.get(days_key)

            if checked and days is not None:
                RouteTimePlanRestriction.objects.create(route_time=route_time, plan=plan, days=days)

        return redirect(self.get_success_url())


class AdminEditRouteTimeView(StaffRequiredMixin, PermissionRequiredMixin, UpdateView):
    """
    Admin view to edit a :class:`flights.models.RouteTime`.  Behaves much like an UpdateView, except the form
    is not a ModelForm and it manages multiple models at once.
    """

    permission_required = 'accounts.can_edit_flights'
    template_name = 'flights/admin/routetime_form.html'
    form_class = RouteTimeForm
    model = RouteTime

    def get_success_url(self):
        return reverse_lazy('admin_route_detail', args=[self.object.route.pk])

    def get_form_kwargs(self, **kwargs):
        kwargs = super(AdminEditRouteTimeView, self).get_form_kwargs(**kwargs)

        kwargs.update({
            'plans': Plan.objects.filter(active=True),
        })

        return kwargs

    def form_valid(self, form):

        old_route_time = RouteTime.objects.filter(id=self.object.id).first()
        old_plane_id = old_route_time.plane_id
        new_plane = form.cleaned_data.get('plane')
        if new_plane is not None and old_plane_id is not None and new_plane.id != old_plane_id:
            Flight.objects.filter(route_time=old_route_time,plane_id=old_plane_id).update(plane=new_plane)

        route_time = form.save()

        RouteTimePlanRestriction.objects.filter(route_time=route_time).delete()

        route_time_plan_restrictions = []
        for plan, restriction_key, days_key in form.plan_fields_keys:
            checked = form.cleaned_data.get(restriction_key)
            days = form.cleaned_data.get(days_key)

            if checked and days is not None:
                restriction = RouteTimePlanRestriction.objects.create(route_time=route_time, plan=plan, days=days)
                route_time_plan_restrictions.append(restriction)

        # Updating flights associated with this RouteTime if a start date is given
        update_flights_start_date = form.cleaned_data.get('update_flights_start_date', None)

        if update_flights_start_date is not None:
            max_seats_corporate = form.cleaned_data.get('max_seats_corporate', None)
            max_seats_companion = form.cleaned_data.get('max_seats_companion', None)
            account_restriction = form.cleaned_data.get('account_restriction', [])
            departure_time = form.cleaned_data.get('departure', None)

            flight_fields = ('max_seats_corporate', 'max_seats_companion', 'account_restriction', 'departure')
            update_fields = [i for i in flight_fields if i in form.changed_data]
            save_fields = filter(lambda x: x != 'account_restriction', update_fields)

            # add arrival along with departure
            if 'departure' in update_fields:
                update_fields.append('arrival')

            flights = route_time.flight_set.filter(departure__gte=update_flights_start_date).only(*update_fields)
            for flight in flights:
                if 'max_seats_corporate' in update_fields:
                    flight.max_seats_corporate = max_seats_corporate

                if 'max_seats_companion' in update_fields:
                    flight.max_seats_companion = max_seats_companion

                if 'departure' in update_fields:
                    flight_date = flight.departure.date()
                    new_departure = arrow.get(datetime.combine(flight_date, departure_time), flight.origin.timezone)
                    flight.departure = new_departure.datetime
                    flight.arrival = new_departure.replace(minutes=route_time.route.duration).datetime

                flight.save(update_fields=save_fields)

                if 'account_restriction' in update_fields:
                    flight.account_restriction.add(*account_restriction)

                FlightPlanRestriction.objects.filter(flight=flight).delete()
                for restriction in route_time_plan_restrictions:
                    FlightPlanRestriction.objects.create(flight=flight, plan=restriction.plan, days=restriction.days)

        return redirect(self.get_success_url())


class AdminRouteSelectFlightsView(StaffRequiredMixin, PermissionRequiredMixin, TemplateView):
    """
    View to select flights from given routes
    """
    permission_required = 'accounts.can_edit_flights'
    template_name = 'flights/admin_routes_select.html'

    def get_success_url(self):
        return reverse_lazy('admin_list_routes')

    def get_context_data(self, **kwargs):
        context = super(AdminRouteSelectFlightsView, self).get_context_data(**kwargs)
        selected_route_pks = self.request.session.pop('selected_routes', None)
        start_date = self.request.session.pop('start_date', None)
        end_date = self.request.session.pop('end_date', None)

        if selected_route_pks is not None and start_date is not None and end_date is not None:
            begin_days = arrow.get(start_date).floor('day')
            end_days = arrow.get(end_date).floor('day')
            day_range = arrow.Arrow.range('day', begin_days, end_days)

            selected_route_times = RouteTime.objects.filter(route__id__in=selected_route_pks)

            for day in day_range:
                day_route_times = None

                # Monday is 0 and Sunday is 6.
                if day.weekday() == 0:
                    day_route_times = selected_route_times.filter(monday=True)
                elif day.weekday() == 1:
                    day_route_times = selected_route_times.filter(tuesday=True)
                elif day.weekday() == 2:
                    day_route_times = selected_route_times.filter(wednesday=True)
                elif day.weekday() == 3:
                    day_route_times = selected_route_times.filter(thursday=True)
                elif day.weekday() == 4:
                    day_route_times = selected_route_times.filter(friday=True)
                elif day.weekday() == 5:
                    day_route_times = selected_route_times.filter(saturday=True)
                elif day.weekday() == 6:
                    day_route_times = selected_route_times.filter(sunday=True)

                day.day_route_times = day_route_times

            context.update({
                'day_range': day_range
            })

            return context

        raise Http404

    def post(self, request, *args, **kwargs):
        """
        Handles POST requests, generating the selected flights.
        """
        selected_flights = request.POST.getlist('selected_flights', None)

        if selected_flights is not None:

            route_time_cache = dict([(str(route_time.id), route_time) for route_time in RouteTime.objects.all().select_related('route', 'route__destination', 'route__origin')])
            route_time_plan_restriction_cache = dict([(str(plan_restriction.route_time_id), plan_restriction) for plan_restriction in RouteTimePlanRestriction.objects.all().select_related('plan')])

            for selected_flight in selected_flights:
                route_time_id, year, month, day = selected_flight.split('|')

                route_time = route_time_cache.get(route_time_id)
                plane = None
                if route_time.plane is not None:
                    plane = route_time.plane
                elif route_time.route.plane is not None:
                    plane = route_time.route.plane

                departure = arrow.now().replace(year=int(year), month=int(month), day=int(day), hour=route_time.departure.hour, minute=route_time.departure.minute).floor('minute')
                arrival = departure.replace(minutes=route_time.route.duration)

                flight = Flight.objects.create(
                    origin=route_time.route.origin,
                    destination=route_time.route.destination,
                    departure=departure.datetime,
                    arrival=arrival.datetime,
                    duration=route_time.route.duration,
                    created_by=request.user,
                    route_time=route_time,
                    flight_number=route_time.flight_number,
                    max_seats_companion=route_time.max_seats_companion,
                    max_seats_corporate=route_time.max_seats_corporate,
                    plane=plane,
                )

                if route_time.account_restriction.exists():
                    flight.account_restriction.add(*route_time.account_restriction.all())

                plan_restrictions = route_time_plan_restriction_cache.get(route_time_id)
                if plan_restrictions:
                    FlightPlanRestriction.objects.create(flight=flight, plan=plan_restriction.plan, days=plan_restriction.days)

            messages.info(self.request, 'The selected flights have been generated sucessfully.')
        else:
            messages.info(self.request, 'No flights were selected.')

        return HttpResponseRedirect(self.get_success_url())


class AdminCreateFlightMessageView(StaffRequiredMixin, PermissionRequiredMixin, SingleObjectMixin, FormView):
    """
    Admin view to add a :class:`flights.models.FlightMessage`
    """

    permission_required = 'accounts.can_edit_flights_limited'
    template_name = 'flights/admin/flight_message.html'
    form_class = FlightMessageForm
    model = Flight

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super(AdminCreateFlightMessageView, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(AdminCreateFlightMessageView, self).get_context_data(**kwargs)

        context.update({
            'flight': self.object,
        })

        return context

    def form_valid(self, form):
        flight = self.object

        flight_message = form.save(commit=False)

        flight_message.flight = flight
        flight_message.created_by = self.request.user
        flight_message.save()

        flight_message.send()

        messages.info(self.request, 'Sent message about flight number "%s" to %d passengers' % (flight.flight_number, flight.get_passengers().count()))

        return redirect('admin_flight_detail', flight.pk)


class ExportFlightsView(StaffRequiredMixin, PermissionRequiredMixin, View):
    """
    A view to export accounts to CSV
    """

    permission_required = 'accounts.can_view_members'

    def get(self, request, *args, **kwargs):
        flights = Flight.objects.all().select_related().order_by('departure')

        date_format = 'YYYY-MM-DD HH:mm:ss ZZ'

        # Create the HttpResponse object with the appropriate CSV header.
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="flights.csv"'

        writer = unicodecsv.writer(response)
        writer.writerow(['Flight ID', 'Flight Number', 'Plane', 'Status', 'Flight Type', 'Origin', 'Destination',
            'Departure', 'Actual Departure', 'Arrival', 'Actual Arrival', 'Duration', 'Total Seats', 'Seats Reserved', 'Seats Available',
            'Companion Seats', 'Max Corporate Seats', 'Max Companion Seats', 'Created', 'Created By', 'Surcharge',
            'Pilot', 'Co-Pilot', 'Founder', 'VIP', 'Accounts Restricted'])

        for flight in flights:
            writer.writerow([
                flight.id,
                flight.flight_number,
                flight.plane,
                flight.get_status_display(),
                flight.get_flight_type_display(),
                flight.origin,
                flight.destination,
                arrow.get(flight.departure).format(date_format),
                arrow.get(flight.actual_departure).format(date_format) if flight.actual_departure else '',
                arrow.get(flight.arrival).format(date_format),
                arrow.get(flight.actual_arrival).format(date_format) if flight.actual_arrival else '',
                flight.duration,
                flight.seats_total,
                flight.seats_total - flight.seats_available,
                flight.seats_available,
                flight.seats_companion,
                flight.max_seats_corporate,
                flight.max_seats_companion,
                arrow.get(flight.created).format(date_format),
                flight.created_by.get_full_name() if flight.created_by else '',
                flight.surcharge,
                flight.pilot.get_full_name() if flight.pilot else '',
                flight.copilot.get_full_name() if flight.copilot else '',
                'Yes' if flight.founder else 'No',
                'Yes' if flight.vip else 'No',
                ', '.join([account.account_name() for account in flight.account_restriction.all()]),
            ])

        return response


class FlightLoadFactorView(StaffRequiredMixin, PermissionRequiredMixin, TemplateView):
    """
    A view to export accounts to CSV
    """

    permission_required = 'accounts.can_view_members'
    template_name = 'flights/admin/load_factor.html'

    def post(self, request, *args, **kwargs):
        data = self.get_context_data()

        # Create the HttpResponse object with the appropriate CSV header.
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="flights.csv"'

        writer = unicodecsv.writer(response)

        writer.writerow(['Overall Load Factor', data['load_overall']])
        writer.writerow(['', ''])
        writer.writerow(['', ''])

        writer.writerow(['Load By Year', ''])
        writer.writerow(['Year', 'Load Factor'])

        for key, value in data['load_by_year'].iteritems():
            writer.writerow([key, value])

        writer.writerow(['', ''])
        writer.writerow(['', ''])

        writer.writerow(['Load by Day of Week', ''])
        writer.writerow(['Day of Week', 'Load Factor'])

        for key, value in data['load_by_day_of_week'].iteritems():
            writer.writerow([key, value])

        writer.writerow(['', ''])
        writer.writerow(['', ''])

        writer.writerow(['Load by Day of Week by Flight', ''])
        writer.writerow(['Day of Week - Flight', 'Load Factor'])

        for key, value in data['load_by_day_of_week_by_flight'].iteritems():
            writer.writerow([key, value])

        writer.writerow(['', ''])
        writer.writerow(['', ''])

        writer.writerow(['Load by Month', ''])
        writer.writerow(['Month', 'Load Factor'])

        for key, value in data['load_by_month'].iteritems():
            writer.writerow([key, value])

        writer.writerow(['', ''])
        writer.writerow(['', ''])

        writer.writerow(['Load by Week', ''])
        writer.writerow(['Week', 'Load Factor'])

        for key, value in data['load_by_week'].iteritems():
            writer.writerow([key, value])

        writer.writerow(['', ''])
        writer.writerow(['', ''])

        writer.writerow(['Load by Day', ''])
        writer.writerow(['Day', 'Load Factor'])

        for key, value in data['load_by_day'].iteritems():
            writer.writerow([key, value])

        return response

    def calculate_load_factor(self, seats_total, seats_reserved):
        load_factor = {}

        for key in seats_total.keys():
            if seats_total[key] == 0:
                load_factor[key] = 0
            else:
                load_factor[key] = (float(seats_reserved[key]) / float(seats_total[key])) * float(100)

        return OrderedDict(sorted(load_factor.items(), key=lambda item: item[0]))

    def get_context_data(self, **kwargs):
        context = super(FlightLoadFactorView, self).get_context_data(**kwargs)

        flights = Flight.objects.exclude(status=Flight.STATUS_CANCELLED).only('flight_number', 'departure', 'seats_total', 'seats_available').order_by('-departure')

        # by day
        seats_total = defaultdict(int)
        seats_reserved = defaultdict(int)
        for flight in flights:
            key = '%04d-%02d-%02d' % flight.departure.timetuple()[:3]
            seats_total[key] += flight.seats_total
            seats_reserved[key] += (flight.seats_total - flight.seats_available)
        load_by_day = self.calculate_load_factor(seats_total, seats_reserved)

        # by week
        seats_total = defaultdict(int)
        seats_reserved = defaultdict(int)
        for flight in flights:
            week = flight.departure - timedelta(days=flight.departure.isoweekday())
            key = '%04d-%02d-%02d' % week.timetuple()[:3]
            seats_total[key] += flight.seats_total
            seats_reserved[key] += (flight.seats_total - flight.seats_available)
        load_by_week = self.calculate_load_factor(seats_total, seats_reserved)

        # by month
        seats_total = defaultdict(int)
        seats_reserved = defaultdict(int)
        for flight in flights:
            key = '%04d-%02d' % flight.departure.timetuple()[:2]
            seats_total[key] += flight.seats_total
            seats_reserved[key] += (flight.seats_total - flight.seats_available)
        load_by_month = self.calculate_load_factor(seats_total, seats_reserved)

        # by year
        seats_total = defaultdict(int)
        seats_reserved = defaultdict(int)
        for flight in flights:
            key = '%s' % flight.departure.timetuple()[:1]
            seats_total[key] += flight.seats_total
            seats_reserved[key] += (flight.seats_total - flight.seats_available)
        load_by_year = self.calculate_load_factor(seats_total, seats_reserved)

        # by day of week overall
        seats_total = defaultdict(int)
        seats_reserved = defaultdict(int)
        for flight in flights:
            key = calendar.day_name[flight.departure.weekday()]
            seats_total[key] += flight.seats_total
            seats_reserved[key] += (flight.seats_total - flight.seats_available)
        load_by_day_of_week = self.calculate_load_factor(seats_total, seats_reserved)

        # by day of week overall by flight number
        seats_total = defaultdict(int)
        seats_reserved = defaultdict(int)
        for flight in flights:
            key = '%s %s' % (calendar.day_name[flight.departure.weekday()], flight.flight_number)
            seats_total[key] += flight.seats_total
            seats_reserved[key] += (flight.seats_total - flight.seats_available)
        load_by_day_of_week_by_flight = self.calculate_load_factor(seats_total, seats_reserved)

        # overall
        overall = Flight.objects.exclude(status=Flight.STATUS_CANCELLED).aggregate(seats_total=Sum('seats_total'), seats_reserved=F('seats_total') - F('seats_available'))
        load_overall = (float(overall['seats_reserved']) / float(overall['seats_total'])) * float(100)

        context.update({
            'load_by_day': load_by_day,
            'load_by_week': load_by_week,
            'load_by_month': load_by_month,
            'load_by_year': load_by_year,
            'load_by_day_of_week': load_by_day_of_week,
            'load_by_day_of_week_by_flight': load_by_day_of_week_by_flight,
            'load_overall': load_overall,
        })
        return context
