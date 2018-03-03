from django.core.urlresolvers import reverse, reverse_lazy
from django.http import HttpResponse
from django.views.generic import View
from django.http.response import Http404
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import TemplateView, FormView, CreateView, UpdateView, DetailView,RedirectView
from django.utils.functional import cached_property
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.conf import settings
from django.contrib import messages
from accounts.mixins import LoginRequiredMixin
from anywhere.forms import AnywhereFlightRequestRouteForm, AnywhereFlightRequestDatesForm, \
    AnywhereFlightRequestPassengersForm, AnywhereUpgradeForm
from anywhere.models import AnywhereFlightRequest, AnywhereFlightSet
from flights.models import Flight
from billing.models import InvalidUpgradeException, IncompleteUpgradeException

import json


class AnywhereLearnView(TemplateView):
    template_name="anywhere/learn_anywhere.html"

class AnywhereUpgradeView(FormView, LoginRequiredMixin):
    template_name = "anywhere/anywhere_plus.html"
    form_class = AnywhereUpgradeForm

    def form_valid(self, form):
        """
        If the account has a valid payment method, we can go straight to the upgrade.
        Otherwise they will need to enter a payment method.
        Args:
            form:

        Returns:

        """
        if self.request.user.account.has_any_payment_method():
            try:
                self.request.user.account.upgrade_anywherebasic_to_plus(user=self.request.user)
                #redirect to anywhere
                messages.success(self.request, "Congratulations!  You are now an Anywhere Plus member!")
                return redirect(reverse_lazy("anywhere_index"))
            except InvalidUpgradeException as inv:
                messages.error(self.request, inv.message)
            except IncompleteUpgradeException as inc:
                messages.error(self.request, inc.message)
            except ReferenceError as re:
                messages.error(self.request, re.message)
            return redirect(reverse_lazy("anywhere_index"))
        else:
            # redirect to payment
            return redirect('payment_anywhereplus')

class AnywhereAvailableFlightListView(LoginRequiredMixin, TemplateView):
    template_name = "anywhere/available_flights.html"

    def get_context_data(self, **kwargs):
        context = super(AnywhereAvailableFlightListView,self).get_context_data(**kwargs)
        flightsets = AnywhereFlightSet.get_available_flightsets()
        page_size=self.request.GET.get('page_size', 5)
        paginator = Paginator(flightsets, page_size)
        page = self.kwargs["page"]
        try:

            context["flightset_list"] = paginator.page(page)
        except PageNotAnInteger:
            context["flightset_list"] = paginator.page(1)
        except EmptyPage:
            context["flightset_list"] = paginator.page(paginator.num_pages)

        return context


class AnywhereFlightRequestCreateView(LoginRequiredMixin, CreateView):
    model = AnywhereFlightRequest
    template_name = 'anywhere/route.html'
    form_class = AnywhereFlightRequestRouteForm

    def get_context_data(self, **kwargs):
        """
        This view also contains the list of available-to-book anywhere flights.
        """
        context = super(AnywhereFlightRequestCreateView,self).get_context_data(**kwargs)
        go_anywhere_link = False
        user = self.request.user
        if settings.RISE_ANYWHERE_REQUEST_GROUPS.__len__() > 0:
            groups = user.groups.filter(name__in=settings.RISE_ANYWHERE_REQUEST_GROUPS)
            if groups is not None:
                go_anywhere_link = True
        else:
            go_anywhere_link = True
        flightsets = AnywhereFlightSet.get_available_flightsets()
        paginator = Paginator(flightsets, settings.ANYWHERE_LANDING_PAGE_LIST_PAGESIZE)
        context["flightset_list"] = paginator.page(1)
        context["go_anywhere_link"] = go_anywhere_link
        return context


    def get_success_url(self):
        return reverse('anywhere_dates', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.status = AnywhereFlightRequest.STATUS_NEW
        form.instance.set_routes()
        return super(AnywhereFlightRequestCreateView, self).form_valid(form)


_breadcrumbs = (
    ('anywhere_route', 'Choose your route', '{object.origin_city} -> {object.destination_city} ({object.trip_type_display})'),
    ('anywhere_dates', 'Choose your dates', '{object.date_crumb}'),
    ('anywhere_passengers', 'Pricing & Sharing', '{object.seats} spots')
)


class AnywhereFlightRequestStage(LoginRequiredMixin, UpdateView):
    model = AnywhereFlightRequest
    stage_title = None
    next_stage = None

    def get_object(self, queryset=None):
        obj = super(AnywhereFlightRequestStage, self).get_object(queryset)

        # return 404 if object does not exist, does not belong to user or IS NOT in the 'New' state (can only modify New requests)
        if obj is None or obj.created_by != self.request.user or obj.status != AnywhereFlightRequest.STATUS_NEW:
            raise Http404('Invalid Flight Request')

        return obj

    def get_success_url(self):
        return reverse(self.next_stage, kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        bread = []

        for route, current_title, prev_title in _breadcrumbs:
            url = reverse(route, kwargs={'pk': self.object.pk})

            if self.request.path == url:
                bread.append((None, current_title, 'active'))
                break
            else:
                bread.append((url, prev_title.format(object=self.object), ''))

        data = super(AnywhereFlightRequestStage, self).get_context_data(**kwargs)

        data.update({
            'breadcrumbs': bread
        })

        return data


class AnywhereFlightRequestRouteView(AnywhereFlightRequestStage):
    template_name = 'anywhere/route.html'
    form_class = AnywhereFlightRequestRouteForm
    stage_title = 'Choose your route'
    next_stage = 'anywhere_dates'


class AnywhereFlightRequestDatesView(AnywhereFlightRequestStage):
    template_name = 'anywhere/dates.html'
    form_class = AnywhereFlightRequestDatesForm
    stage_title = 'Choose your dates'
    next_stage = 'anywhere_passengers'

    def form_valid(self, form):
        error_flag = False
        if form.cleaned_data['depart_date'] is None:
            form.add_error('depart_date','Please enter a Departure Date')
            error_flag = True
        if self.object.is_round_trip:
            if form.cleaned_data['return_date'] is None:
                form.add_error('return_date','Please enter a Return Date')
                error_flag = True
        if error_flag:
            return self.form_invalid(form)
        else:
            return super(AnywhereFlightRequestDatesView, self).form_valid(form)


class AnywhereFlightRequestPassengersView(AnywhereFlightRequestStage):
    template_name = 'anywhere/passengers.html'
    form_class = AnywhereFlightRequestPassengersForm
    stage_title = 'Choose your passengers'
    next_stage = 'anywhere_summary'

    def get_context_data(self, **kwargs):
        context = super(AnywhereFlightRequestPassengersView,self).get_context_data(**kwargs)
        id = self.kwargs.get("pk")
        request = get_object_or_404(AnywhereFlightRequest,id=id)

        if request is not None:
             # if seats > seats_required default, adjust seats_required
            if request.seats > request.seats_required:
                request.seats_required = request.seats
                request.save()
            context.update({
                'outbound_route': request.outbound_route,
                'return_route': request.return_route,
                'estimated_cost': request.estimated_cost,
                'two_seat_price': request.two_seat_price,
                'three_seat_price': request.three_seat_price,
                'four_seat_price': request.four_seat_price,
                'five_seat_price': request.five_seat_price,
                'six_seat_price': request.six_seat_price,
                'seven_seat_price': request.seven_seat_price,
                'eight_seat_price': request.eight_seat_price
            })

        return context

    def form_valid(self, form):
        # update status to Pending to prevent further changes
        form.instance.status = AnywhereFlightRequest.STATUS_PENDING
        response = super(AnywhereFlightRequestPassengersView, self).form_valid(form)
        #send out the notification email
        form.instance.send_request_received_email()
        return response

class AnywhereFlightRequestSummary(LoginRequiredMixin, DetailView):
    template_name = 'anywhere/summary.html'
    model = AnywhereFlightRequest

    def get_context_data(self, **kwargs):
        context = super(AnywhereFlightRequestSummary,self).get_context_data(**kwargs)
        id = self.kwargs.get("pk")
        request = get_object_or_404(AnywhereFlightRequest,id=id)
        if request is not None:
            seat_price = request.other_seat_price(request.seats_required)
            context.update({
                'your_price': seat_price * request.seats
            })

        return context

    def get_object(self, queryset=None):
        obj = super(AnywhereFlightRequestSummary, self).get_object(queryset)

        # return 404 if object does not exist, does not belong to user or IS in the 'New' state (no summary available)
        if obj is None or obj.created_by != self.request.user or obj.status == AnywhereFlightRequest.STATUS_NEW:
            raise Http404('Invalid Flight Request')

        return obj


class AnywhereFlightInfoView(DetailView, LoginRequiredMixin):
    template_name = 'anywhere/flight_info.html'
    model = AnywhereFlightSet

    def get_object(self, queryset=None):
        #we don't want to expose a guessable PK in the URL so we are using GUIDs to load the flightsets.
        #theoretically I think we could override the PK field definition to use a GUID for the PK as well but this way
        #the PK isn't actually ever exposed at all so I like this option better.
        flightset_key = self.kwargs.get("slug")
        obj= self.model.objects.filter(public_key=flightset_key).first()
        return obj

    def get_context_data(self, **kwargs):
        context = super(AnywhereFlightInfoView,self).get_context_data(**kwargs)
        context["is_logged_in"] = self.is_logged_on()
        context["redirect_link"] = self.get_redirect_link()

        flightset_key = self.kwargs.get("slug")
        #if user is logged on and is booked on this flight, they can invite.
        obj= self.model.objects.filter(public_key=flightset_key).first()
        if self.is_logged_on() and obj.leg1.is_booked_by_user(self.request.user):
            context["invite_ok"] = True
            context["book_ok"] = False
        elif obj.leg1.seats_available > 0:
            context["invite_ok"] = False
            context["book_ok"] = True
        else:
            context["invite_ok"] = False
            context["book_ok"] = False

        context["invitation_link"] = reverse_lazy("invite_anywhere", kwargs={"slug":flightset_key})
        return context

    def get_redirect_link(self):
        flightset_key = self.kwargs.get('slug', None)
        return reverse_lazy("join_anywhere", kwargs={"slug":flightset_key})

    def is_logged_on(self):
         if self.request.user is not None and self.request.user.is_authenticated():
             return True
         return False

class ViewInviteRedirectView(RedirectView):
    pattern_name = 'login_anywhere'
    redirect = "anywhere_flight_info"
    model = AnywhereFlightSet

    def get_redirect_url(self, *args, **kwargs):
        """
        Redirect to booking if they are logged in.
        Redirect to login/signup if they are not.
        We have to put the flight id in session just in case they end up in signup.
        """
        flightset_public_key = self.kwargs.get('slug')
        self.request.session['flightset_public_key'] = flightset_public_key
        if self.request.user.is_authenticated():
            self.pattern_name='anywhere_flight_info'
            return reverse_lazy(self.pattern_name,kwargs={'slug': flightset_public_key})

        return "%s?key=%s&next=%s" % (reverse_lazy(self.pattern_name), flightset_public_key, reverse_lazy(self.redirect, kwargs={'slug':flightset_public_key }))


class JoinAnywhereRedirectView(LoginRequiredMixin, RedirectView):
    anywhere_payment = 'payment_anywhere_form'
    regular_payment = ''
    redirect = "book_anywhere"
    model = AnywhereFlightSet

    def get_redirect_url(self, *args, **kwargs):
        """
        Redirect to anywhere payment if they have no payment info.
        Redirect to booking otherwise, however add flags for whether we will send them to verification afterwards.
        """
        query_string = ""
        flightset_public_key = self.kwargs.get('slug')
        self.request.session['flightset_public_key'] = flightset_public_key
        has_payment_method=self.request.user.account.has_any_payment_method()
        user = self.request.user
        account = user.account
        if account.is_anywhere_only() and not has_payment_method:
            messages.error(self.request, 'You must set up a valid payment method before joining a RISE ANYWHERE flight.')
            return reverse_lazy(self.anywhere_payment,kwargs={'slug': flightset_public_key})

        if self.request.user.account.is_ach() and self.request.user.account.need_verify_bank_account():
            query_string="v=a"
        elif self.request.user.account.is_manual():
            query_string="v=m"

        return "%s?%s" % (reverse_lazy(self.redirect, kwargs={'slug':flightset_public_key}), query_string)

class AnywhereInvitationView(LoginRequiredMixin, DetailView):
    template_name = 'anywhere/invitations.html'
    model = AnywhereFlightSet

    def get_object(self, queryset=None):
        #we don't want to expose a guessable PK in the URL so we are using GUIDs to load the flightsets.
        #theoretically I think we could override the PK field definition to use a GUID for the PK as well but this way
        #the PK isn't actually ever exposed at all so I like this option better.
        flightset_key = self.kwargs.get("slug")
        obj= self.model.objects.filter(public_key=flightset_key).first()
        return obj

    def get_context_data(self, **kwargs):
        context = super(AnywhereInvitationView,self).get_context_data(**kwargs)
        context["invitation_link"] = self.get_redirect_link()
        context["send_email_link"] = self.get_email_link()
        context["cloudsponge_uri"] = settings.CLOUDSPONGE_URI
        return context

    def get_redirect_link(self):
        flightset_key = self.kwargs.get('slug', None)
        return reverse_lazy("view_anywhere_invite", kwargs={"slug":flightset_key})

    def get_email_link(self):
        flightset_key = self.kwargs.get('slug', None)
        return reverse_lazy("email_invitations", kwargs={"slug":flightset_key})

class AnywhereSendInvitationsView(View, LoginRequiredMixin):
    def post(self, *args, **kwargs):
        email_list = self.request.POST['emails']
        flightset_key = self.kwargs.get('slug', None)
        flightset = AnywhereFlightSet.objects.filter(public_key=flightset_key).first()
        response_data = {}
        try:
            flightset.send_email_invitations(email_list)
            response_data["success"] = True
        except Exception as e:
            response_data["success"] = False
            response_data["errors"] = "There was an error sending the email invitations."

        return HttpResponse(json.dumps(response_data), content_type="application/json")
