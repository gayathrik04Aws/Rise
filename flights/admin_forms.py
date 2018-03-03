from __future__ import division
from django import forms
from django.db.models import Q
from localflavor.us.us_states import STATE_CHOICES
from django.contrib.auth.models import Permission
from django.forms.models import inlineformset_factory
from django.conf import settings

from datetime import datetime, timedelta
import pytz
import arrow
import re

from accounts.models import User, Account, UserProfile
from accounts.fields import UserModelChoiceField
from billing.models import Plan
from .models import (
    Airport, Plane, Flight, Route, RouteTime, RouteTimePlanRestriction, FlightMessage,
    FlightPlanSeatRestriction, AnywhereFlightDetails
)
from anywhere.models import AnywhereFlightRequest, AnywhereRoute
from reservations.models import Reservation
from . import const


class AirportForm(forms.ModelForm):
    """
    A form for adding/editing an airport
    """

    state = forms.ChoiceField(choices=STATE_CHOICES, initial='TX')

    class Meta:
        model = Airport
        fields = ('name', 'street_1', 'street_2', 'city', 'state', 'postal_code', 'code', 'timezone', 'details')

    def __init__(self, *args, **kwargs):
        super(AirportForm, self).__init__(*args, **kwargs)

        self.fields['name'].widget.attrs.update({'placeholder': 'Airport Name'})
        self.fields['name'].error_messages = {'required': 'Airport Name is requried.'}

        self.fields['code'].widget.attrs.update({'placeholder': 'Airport Code'})
        self.fields['code'].error_messages = {'required': 'Airport Code is requried.'}

        self.fields['street_1'].widget.attrs.update({'placeholder': 'Street'})
        self.fields['street_1'].error_messages = {'required': 'Street address is requried.'}

        self.fields['street_2'].widget.attrs.update({'placeholder': 'Street (optional)'})

        self.fields['city'].widget.attrs.update({'placeholder': 'City'})
        self.fields['city'].error_messages = {'required': 'City is requried.'}

        self.fields['state'].widget.attrs.update({'placeholder': 'City'})
        self.fields['state'].error_messages = {'required': 'State is requried.'}
        self.fields['state'].empty_label = None

        self.fields['postal_code'].widget.attrs.update({'placeholder': 'Postal Code'})
        self.fields['postal_code'].error_messages = {'required': 'Postal Code is requried.'}

        self.fields['details'].widget.attrs.update({'placeholder': 'Details'})
        self.fields['details'].error_messages = {'required': 'Details is requried.'}


class PlaneForm(forms.ModelForm):
    """
    A form for adding/editing a :class:`flights.models.Plane`
    """

    class Meta:
        model = Plane
        fields = ('model', 'registration', 'seats',)

    def __init__(self, *args, **kwargs):
        super(PlaneForm, self).__init__(*args, **kwargs)

        self.fields['model'].widget.attrs.update({'placeholder': 'Plane Model'})
        self.fields['model'].error_messages = {'required': 'Model is requried.'}

        self.fields['registration'].widget.attrs.update({'placeholder': 'Tail Number'})
        self.fields['registration'].error_messages = {'required': 'Tail Number is requried.'}

        self.fields['seats'].widget.attrs.update({'placeholder': 'Seats'})
        self.fields['seats'].error_messages = {'required': 'Seats is requried.'}


class FlightForm(forms.Form):
    """
    A form for creating/editing a :class:`flights.models.Flight` and related :class:`flights.models.FlightPlanRestriction`
    instances for that flight.  Behaves very similarly to a ModelForm except that it deals with multiple models.
    """
    TYPE_CHOICES = Flight.TYPE_CHOICES[:]

    origin = forms.ModelChoiceField(Airport.objects.all(), empty_label="Origin Airport",
        error_messages={'required': 'Origin Airport is required.'})
    destination = forms.ModelChoiceField(Airport.objects.all(), empty_label="Destination Airport",
        error_messages={'required': 'Destination Airport is required.'})
    plane = forms.ModelChoiceField(Plane.objects.all(), empty_label="Select Plane", required=False)
    start_date = forms.DateField(widget=forms.DateInput(format="%m/%d/%Y", attrs={'placeholder': 'MM / DD / YEAR'}),
        label="Start Date", error_messages={'required': 'Start Date is required.'})
    takeoff_time = forms.TimeField(widget=forms.TimeInput(format="%H:%M", attrs={'placeholder': '00:00'}),
        label='Takeoff Time', error_messages={'required': 'Takeoff time is required.'})
    # TimeInput will work for duration as long as durations are under 24 hours, which they should always be
    # given the business model here.

    duration = forms.TimeField(widget=forms.TimeInput(format="%H:%M", attrs={'placeholder': '00:00'}), label="Duration",
        error_messages={'required': 'Duration length is required.'})
    pilot = UserModelChoiceField(User.objects.filter(groups__name='Pilot'), empty_label="Pilot Name", required=False)
    copilot = UserModelChoiceField(User.objects.filter(groups__name='Pilot'), empty_label="Co-Pilot Name", required=False)
    flight_number = forms.CharField(widget=forms.TextInput(attrs={'placeholder': 'Flight Number'}), max_length=16,
        error_messages={'required': 'Flight Number is required.'})

    # comps display that flight_type could be multiple selected options, but model is a single CharField with single choice
    flight_type = forms.ChoiceField(label="Flight Type", choices=TYPE_CHOICES)
    has_surcharge = forms.BooleanField(label="This flight has a surcharge", required=False,
        widget=forms.CheckboxInput(attrs={'class': 'flight-surcharge-checkbox'}))
    surcharge = forms.DecimalField(label="surcharge", required=False, decimal_places=2, min_value=0,
        widget=forms.TextInput(attrs={'class': 'surcharge fr', 'placeholder': '$0.00'}))

    # Fields for billing plan restriction
    has_restrictions = forms.BooleanField(label="Only available to some Membership Tiers", required=False,
        widget=forms.CheckboxInput(attrs={'class': 'reveal-checkbox'}))
    # TODO: handle these more dynamically so that as billing plans are added/removed this form does not need to change?
    has_express_restriction = forms.BooleanField(required=False, label="Express",
        widget=forms.CheckboxInput(attrs={'class': 'reveal-checkbox'}))
    express_restriction_days = forms.IntegerField(min_value=0, required=False,
        widget=forms.NumberInput(attrs={'placeholder': 'Beginning (i.e. 21 days before, 14 days before, etc.).', 'class': 'beginning-input'}))
    has_executive_restriction = forms.BooleanField(required=False, label="Executive",
        widget=forms.CheckboxInput(attrs={'class': 'reveal-checkbox'}))
    executive_restriction_days = forms.IntegerField(min_value=0, required=False,
        widget=forms.NumberInput(attrs={'placeholder': 'Beginning (i.e. 21 days before, 14 days before, etc.).', 'class': 'beginning-input'}))
    has_chairman_restriction = forms.BooleanField(required=False, label="Chairman",
        widget=forms.CheckboxInput(attrs={'class': 'reveal-checkbox'}))
    chairman_restriction_days = forms.IntegerField(min_value=0, required=False,
        widget=forms.NumberInput(attrs={'placeholder': 'Beginning (i.e. 21 days before, 14 days before, etc.).', 'class': 'beginning-input'}))
    # has_corporate_restriction = forms.BooleanField(required=False, label="Corporate")
    # corporate_restriction_days = forms.IntegerField(min_value=0, required=False,
    #     widget=forms.NumberInput(attrs={'placeholder': 'Beginning (i.e. 21 days before, 14 days before, etc.).'}))
    allowed_corporations = forms.ModelMultipleChoiceField(Account.objects.filter(account_type=Account.TYPE_CORPORATE),
        widget=forms.CheckboxSelectMultiple, required=False)

    vip = forms.BooleanField(label="This flight is restricted to VIP accounts.", required=False,
        widget=forms.CheckboxInput(attrs={'class': 'flight-vip-checkbox'}))
    founder = forms.BooleanField(label="This flight is restricted to Founder accounts.", required=False,
        widget=forms.CheckboxInput(attrs={'class': 'flight-founder-checkbox'}))

    corporate_max = forms.IntegerField(widget=forms.TextInput(attrs={'placeholder': 'Enter Limit', 'class': 'fr'}), min_value=0, required=True)
    companion_max = forms.IntegerField(widget=forms.TextInput(attrs={'placeholder': 'Enter Limit', 'class': 'fr'}), min_value=0, required=True)

    class Meta:
        fields = ('origin', 'destination', 'plane', 'start_date', 'takeoff_time', 'duration', 'pilot', 'copilot',
                  'flight_number', 'flight_type', 'has_surcharge', 'surcharge', 'has_restrictions',
                  'has_express_restriction', 'express_restriction_days', 'has_executive_restriction',
                  'executive_restriction_days', 'has_chairman_restriction', 'chairman_restriction_days',
                  'allowed_corporations', 'corporate_min', 'corporate_max', 'vip', 'founder')

    def __init__(self, *args, **kwargs):
        instance = kwargs.pop('instance', None)
        initial = kwargs.pop('initial')
        object_data = {}
        if instance is None:
            # if we didn't get an instance, instantiate a new one
            self.instance = Flight()
        else:
            self.instance = instance
            object_data['has_surcharge'] = bool(instance.surcharge)
            object_data['surcharge'] = instance.surcharge
            object_data['origin'] = instance.origin
            object_data['destination'] = instance.destination
            object_data['corporate_max'] = instance.max_seats_corporate
            object_data['companion_max'] = instance.max_seats_companion
            object_data['flight_type'] = instance.flight_type
            object_data['flight_number'] = instance.flight_number
            object_data['duration'] = instance.duration_as_time()
            object_data['start_date'] = instance.departure.astimezone(pytz.timezone(instance.origin.timezone)).date()
            object_data['takeoff_time'] = instance.departure.astimezone(pytz.timezone(instance.origin.timezone)).timetz()
            object_data['pilot'] = instance.pilot
            object_data['copilot'] = instance.copilot
            object_data['allowed_corporations'] = instance.account_restriction.all()
            object_data['vip'] = instance.vip
            object_data['founder'] = instance.founder
            object_data['plane'] = instance.plane

            flight_restrictions = instance.flightplanrestriction_set.all()
            if flight_restrictions:
                object_data['has_restrictions'] = True
                restrictions = {restriction.plan.name.lower(): restriction for restriction in flight_restrictions}

                express_restriction = restrictions.get('express')
                if express_restriction:
                    object_data['has_express_restriction'] = True
                    object_data['express_restriction_days'] = express_restriction.days

                exec_restriction = restrictions.get('executive')
                if exec_restriction:
                    object_data['has_executive_restriction'] = True
                    object_data['executive_restriction_days'] = exec_restriction.days

                chairman_restriction = restrictions.get('chairman')
                if chairman_restriction:
                    object_data['has_chairman_restriction'] = True
                    object_data['chairman_restriction_days'] = chairman_restriction.days

        if initial:
            object_data.update(initial)

        super(FlightForm, self).__init__(initial=object_data, *args, **kwargs)

    def clean(self, *args, **kwargs):
        cleaned_data = super(FlightForm, self).clean(*args, **kwargs)

        origin = cleaned_data.get('origin')
        destination = cleaned_data.get('destination')
        if origin == destination:
            raise forms.ValidationError("Flight cannot have the same origin and destination.")

        return cleaned_data

    def clean_has_express_restriction(self):
        has_express_restriction = self.cleaned_data.get('has_express_restriction')
        if has_express_restriction and not Plan.objects.filter(name__iexact='Express').exists():
            raise forms.ValidationError("""Unknown flight plan 'Express'""")

        return has_express_restriction

    def clean_express_restriction_days(self):
        days = self.cleaned_data.get('express_restriction_days', None)
        restriction = self.cleaned_data.get('has_express_restriction')
        # allow days == 0 to be valid although it would fail the 'not days' check
        if restriction and (not days and not days == 0):
            raise forms.ValidationError('Number of days for Express plans not set')

        return days

    def clean_has_executive_restriction(self):
        has_executive_restriction = self.cleaned_data.get('has_executive_restriction')
        if has_executive_restriction and not Plan.objects.filter(name__iexact='Executive').exists():
            raise forms.ValidationError("""Unknown flight plan 'Executive'""")

        return has_executive_restriction

    def clean_executive_restriction_days(self):
        days = self.cleaned_data.get('executive_restriction_days', None)
        restriction = self.cleaned_data.get('has_executive_restriction')
        # allow days == 0 to be valid although it would fail the 'not days' check
        if restriction and (not days and not days == 0):
            raise forms.ValidationError('Number of days for Executive plans not set')

        return days

    def clean_has_chairman_restriction(self):
        has_chairman_restriction = self.cleaned_data.get('has_chairman_restriction')
        if has_chairman_restriction and not Plan.objects.filter(name__iexact='Chairman').exists():
            raise forms.ValidationError("""Unknown flight plan 'Chairman'""")

        return has_chairman_restriction

    def clean_chairman_restriction_days(self):
        days = self.cleaned_data.get('chairman_restriction_days', None)
        restriction = self.cleaned_data.get('has_chairman_restriction')
        # allow days == 0 to be valid although it would fail the 'not days' check
        if restriction and (not days and not days == 0):
            raise forms.ValidationError('Number of days for Chairman plans not set')

        return days

    def clean_has_corporate_restriction(self):
        has_corporate_restriction = self.cleaned_data.get('has_corporate_restriction')
        if has_corporate_restriction and not Plan.objects.filter(name__iexact='Corporate').exists():
            raise forms.ValidationError("""Unknown flight plan 'Corporate'""")

        return has_corporate_restriction

    def clean_corporate_restriction_days(self):
        days = self.cleaned_data.get('corporate_restriction_days', None)
        restriction = self.cleaned_data.get('has_corporate_restriction')
        # allow days == 0 to be valid although it would fail the 'not days' check
        if restriction and (not days and not days == 0):
            raise forms.ValidationError('Number of days for Corporate plans not set')

        return days

    def clean_surcharge(self):
        """
        If has_surcharge, validates surcharge_amount is filled in.  Requires that surcharge_amount be listed
        AFTER has_surcharge in the fields list
        """
        has_surcharge = self.cleaned_data.get('has_surcharge')
        surcharge_amount = self.cleaned_data.get('surcharge')
        if has_surcharge and not surcharge_amount:
            raise forms.ValidationError("No surcharge amount specified.")

        return surcharge_amount

    def set_plan_restriction(self, restricted_object):
        """
        Set up billing plan based restrictions for an object such as a :class:`flights.models.Flight` or :class:`flights.models.RouteTime`.
        Calls `restricted_object.set_plan_restrictions()` and passes in a list of two-tuples of [('PlanName', days)] where
        PlanName is a string name of a billing plan and days is an integer number of days prior to the flight which it can
        be reserved by members on that billing plan.

        """
        assert(hasattr(restricted_object, 'set_plan_restrictions'))

        plan_restrictions = []
        if self.cleaned_data.get('has_express_restriction'):
            plan_restrictions.append(('Express', self.cleaned_data.get('express_restriction_days')))

        if self.cleaned_data.get('has_executive_restriction'):
            plan_restrictions.append(('Executive', self.cleaned_data.get('executive_restriction_days')))

        if self.cleaned_data.get('has_chairman_restriction'):
            plan_restrictions.append(('Chairman', self.cleaned_data.get('chairman_restriction_days')))

        if self.cleaned_data.get('has_corporate_restriction'):
            plan_restrictions.append(('Corporate', self.cleaned_data.get('corporate_restriction_days')))

        restricted_object.set_plan_restrictions(restrictions=plan_restrictions)

    def save_flight(self, created_by=None):
        flight = self.instance

        flight.origin = self.cleaned_data.get('origin')
        flight.destination = self.cleaned_data.get('destination')
        flight.flight_number = self.cleaned_data.get('flight_number')
        flight.plane = self.cleaned_data.get('plane')
        flight.pilot = self.cleaned_data.get('pilot')
        flight.copilot = self.cleaned_data.get('copilot')
        flight.flight_type = self.cleaned_data.get('flight_type')

        if created_by:
            flight.created_by = created_by

        if self.cleaned_data.get('fun_flight'):
            flight.flight_type = Flight.TYPE_FUN

        if self.cleaned_data.get('promo_flight'):
            flight.flight_type = Flight.TYPE_PROMOTION

        has_surcharge = self.cleaned_data.get('has_surcharge')
        surcharge = self.cleaned_data.get('surcharge')
        if surcharge:
            flight.surcharge = surcharge

        corporate_max = self.cleaned_data.get('corporate_max', None)
        if corporate_max is not None:
            flight.max_seats_corporate = corporate_max

        companion_max = self.cleaned_data.get('companion_max')
        if companion_max:
            flight.max_seats_companion = companion_max

        # take our start date and takeoff time and put them together
        tz = pytz.timezone(flight.origin.timezone)
        takeoff_at = self.cleaned_data.get('takeoff_time')

        departure_time = datetime.combine(self.cleaned_data.get('start_date'), takeoff_at)
        # workaround to get the time correct.  using .replace(tzinfo=XXXX) can get weird results due to dst stuff.
        # localize the naive datetime comes from http://stackoverflow.com/a/25390097
        departure_time = tz.localize(departure_time)
        flight.departure = departure_time.astimezone(pytz.UTC)

        # Convert duration as a time object to seconds from 00:00:00
        duration = self.cleaned_data.get('duration')
        duration_as_minutes = (duration.hour * 60) + duration.minute
        flight.duration = duration_as_minutes

        flight.arrival = flight.departure + timedelta(minutes=flight.duration)

        vip = self.cleaned_data.get('vip', None)
        if vip is not None:
            flight.vip = vip

        founder = self.cleaned_data.get('founder', None)
        if founder is not None:
            flight.founder = founder

        # TODO: set seats_total and seats_available?
        flight.save()

        account_restrictions = self.cleaned_data.get('allowed_corporations', [])
        flight.account_restriction = account_restrictions

        self.set_plan_restriction(restricted_object=flight)

        return flight


class FlightSetStatusForm(forms.ModelForm):

    class Meta:
        model = Flight
        fields = ('status',)

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user')
        super(FlightSetStatusForm, self).__init__(*args, **kwargs)

        if self.instance:
            can_edit = user.has_perm('accounts.can_edit_flights') or user.has_perm('accounts.can_update_flights') or user.has_perm('accounts.can_edit_flights_limited')

            choices = []
            for choice in self.instance.status_choices():
                if can_edit:
                    choices.append(choice)

            self.fields['status'].choices = (('', 'Mark Flight As'),) + tuple(choices)


class FlightPlanSeatRestrictionForm(forms.ModelForm):

    flight = forms.ModelChoiceField(Flight.objects.all(), required=False)
    seats = forms.IntegerField(
        widget=forms.TextInput(attrs={'placeholder': 'Enter Limit', 'class': 'fl'}), min_value=0, required=True)

    class Meta:
        model = FlightPlanSeatRestriction
        fields = ('flight', 'plan', 'seats')

    def __init__(self, *args, **kwargs):
        super(FlightPlanSeatRestrictionForm, self).__init__(*args, **kwargs)

        self.fields['plan'].error_messages = {'required': 'Select a plan for the seat restricton.'}
        self.fields['seats'].error_messages = {'required': 'Please specify the number of seats allowed.'}

        self.fields['plan'].empty_label = 'Select Type'


FlightPlanSeatRestrictionFormSet = inlineformset_factory(Flight, FlightPlanSeatRestriction,
                                                         form=FlightPlanSeatRestrictionForm, extra=1, can_delete=True)


class RouteForm(forms.ModelForm):

    duration = forms.TimeField(widget=forms.TimeInput(format='%H:%M', attrs={'placeholder': '00:00'}), error_messages={'required': 'Duration is required in format H:MM.'})

    plane = forms.ModelChoiceField(Plane.objects.all(), empty_label="Select Plane", required=False)
    class Meta:
        model = Route
        fields = ('name', 'origin', 'destination', 'duration','plane')

    def __init__(self, *args, **kwargs):
        super(RouteForm, self).__init__(*args, **kwargs)
        if self.instance.duration:
            self.initial['duration'] = self.instance.duration_as_timedelta()

        self.fields['name'].error_messages = {'required': 'Route name is required.'}
        self.fields['origin'].empty_label = None
        self.fields['destination'].empty_label = None

    def clean(self):
        origin = self.cleaned_data.get('origin')
        destination = self.cleaned_data.get('destination')

        if origin == destination:
            self.add_error(None, 'Origin and destination cannot be the same airport')

        return self.cleaned_data

    def clean_duration(self):
        # Convert duration as a time object to seconds from 00:00:00
        duration = self.cleaned_data.get('duration')
        duration_as_minutes = (duration.hour * 60) + (duration.minute)
        duration = duration_as_minutes

        return duration


class RouteTimeForm(forms.ModelForm):
    """
    A form for creating/editing a :class:`flights.models.RouteTime` and related :class:`flights.models.RouteTime` and
    :class:`flights.models.RouteTimePlanRestriction` instances for that flight.  Behaves very similarly to a ModelForm
    except that it deals with multiple models.
    """

    account_restriction = forms.ModelMultipleChoiceField(required=False, queryset=Account.objects.filter(account_type=Account.TYPE_CORPORATE))
    update_flights_start_date = forms.DateField(required=False, widget=forms.DateInput(format='%m/%d/%Y'), input_formats=('%m/%d/%Y', '%m/%d/%y',))
    plane = forms.ModelChoiceField(Plane.objects.all(), empty_label="Select Plane", required=False)
    class Meta:
        model = RouteTime
        fields = ('flight_number', 'departure', 'sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday',
                  'saturday', 'account_restriction', 'max_seats_corporate', 'max_seats_companion','plane')

    def __init__(self, plans, *args, **kwargs):
        self.plans = plans

        super(RouteTimeForm, self).__init__(*args, **kwargs)

        self.fields['departure'].widget = forms.TimeInput(format="%H:%M", attrs={'placeholder': '00:00'})

        self.plan_fields_keys = []

        for plan in plans:
            self.fields['plan_%s_restriction' % plan.id] = forms.BooleanField(required=False)
            self.fields['plan_%s_days' % plan.id] = forms.IntegerField(min_value=0, required=False)

            self.plan_fields_keys.append((plan, 'plan_%s_restriction' % plan.id, 'plan_%s_days' % plan.id))

        if self.instance:
            plan_restrictions = RouteTimePlanRestriction.objects.filter(route_time=self.instance).select_related('plan')
            for plan_restriction in plan_restrictions:
                self.initial['plan_%s_restriction' % plan_restriction.plan_id] = True
                self.initial['plan_%s_days' % plan_restriction.plan_id] = plan_restriction.days

    def plan_fields(self):
        for plan, restriction, days in self.plan_fields_keys:
            yield (plan, self.__getitem__(restriction), self.__getitem__(days))

    def clean_update_flights_start_date(self):
        update_flights_start_date = self.cleaned_data.get('update_flights_start_date')

        if update_flights_start_date is not None and update_flights_start_date < arrow.now().floor('day').date():
            self.add_error('update_flights_start_date', 'Select an update start date that is not in the past.')

        return update_flights_start_date


class RouteListForm(forms.Form):
    route_list = forms.ModelMultipleChoiceField(queryset=Route.objects.all(), widget=forms.CheckboxSelectMultiple, error_messages={'required': 'No routes were selected.'})
    start_date = forms.DateField(widget=forms.DateInput(format='%m/%d/%Y'), input_formats=('%m/%d/%Y', '%m/%d/%y',), error_messages={'required': 'Start Date is required.'})
    end_date = forms.DateField(widget=forms.DateInput(format='%m/%d/%Y'), input_formats=('%m/%d/%Y', '%m/%d/%y',), error_messages={'required': 'End Date is required.'})

    def clean_start_date(self):
        start_date = self.cleaned_data.get('start_date')

        if start_date < arrow.now().floor('day').date():
            self.add_error('start_date', 'Select a start date that is not in the past.')

        return start_date

    def clean_end_date(self):
        end_date = self.cleaned_data.get('end_date')

        if end_date < arrow.now().floor('day').date():
            self.add_error('end_date', 'Select an end date that is not in the past.')

        return end_date

    def clean(self):
        start_date = self.cleaned_data.get('start_date')
        end_date = self.cleaned_data.get('end_date')

        if start_date > end_date:
            self.add_error('end_date', 'Select an end date after the start date.')


class FlightListFilterForm(forms.Form):
    """
    A form for handling the various flight filtering options on the AdminFlightListView
    """

    class TypeChoices:
        ALL = ''
        PROMO = 'promo'
        FUN = 'fun'

    TYPE_CHOICES = (
        (TypeChoices.ALL, 'All Flights'),
        (TypeChoices.PROMO, 'Promo Flights'),
        (TypeChoices.FUN, 'Fun Flights')
    )
    date = forms.DateField(widget=forms.Select(), required=False)
    type = forms.ChoiceField(choices=TYPE_CHOICES, required=False)

    def __init__(self, date_choices, *args, **kwargs):
        super(FlightListFilterForm, self).__init__(*args, **kwargs)
        # seem to need both of these specified or the form does not work
        self.fields['date'].choices = date_choices
        self.fields['date'].widget = forms.Select(choices=date_choices)


class FlightMessageForm(forms.ModelForm):
    """
    A form for creating a flight message
    """
    message = forms.CharField(widget=forms.Textarea)
    class Meta:
        model = FlightMessage
        fields = ('message',)


class CancelFlightForm(forms.Form):
    """
    A form to be used when canceling a flight
    """

    message = forms.CharField(max_length=160, error_messages={'required': 'Message is required.'})


class DelayedFlightForm(forms.Form):
    """
    A form to be used when delaying a flight to set a delayed message and time
    """

    departure_date = forms.DateField(widget=forms.DateInput(format="%m/%d/%Y", attrs={'placeholder': 'MM / DD / YEAR'}), error_messages={'required': 'Departure date is required.'})
    departure_time = forms.TimeField(widget=forms.TimeInput(format="%H:%M", attrs={'placeholder': '00:00'}), error_messages={'required': 'New departure time is required.'})
    message = forms.CharField(max_length=160, error_messages={'required': 'Message is required.'})


class FlightBookMemberForm(forms.Form):
    """
    A form to be used when selecting a member for booking on a flight
    """
    active_accounts = Account.objects.filter(status=Account.STATUS_ACTIVE)
    perm = Permission.objects.get(codename='can_fly')
    #active_users = User.objects.filter(Q(groups__permissions=perm) | Q(user_permissions=perm), is_active=True,account=active_accounts).distinct().order_by('last_name', 'first_name')
    active_users = User.objects.filter(Q(groups__permissions=perm) | Q(user_permissions=perm), is_active=True,account=active_accounts).distinct().values_list("id", flat=True)
    profiles = UserProfile.objects.filter(Q(user__id__in=active_users) | (Q(user__isnull=True) & Q(account=active_accounts) )).order_by('last_name', 'first_name')
    member = forms.ModelChoiceField(profiles, error_messages={'required': 'Member is required.'})

    def __init__(self, *args, **kwargs):
        super(FlightBookMemberForm, self).__init__(*args, **kwargs)
        self.fields['member'].label_from_instance = lambda obj: "%s" % obj.get_full_name()

class AnywhereFlightBookMemberForm(forms.Form):
    """
    A form to be used when selecting a member for booking on a flight
    """
    active_accounts = Account.objects.filter(status=Account.STATUS_ACTIVE)
    active_users = User.objects.filter(is_active=True,account=active_accounts).distinct().order_by('last_name', 'first_name')
    profiles = UserProfile.objects.filter(Q(user__id__in=active_users) | (Q(user__isnull=True) & Q(account=active_accounts))).order_by('last_name', 'first_name')

    member = forms.ModelChoiceField(profiles, error_messages={'required': 'Member is required.'})
    add_to_existing_reservation = forms.BooleanField(label="Add to flight creator's reservation?", required=False)

    def __init__(self, *args, **kwargs):
        super(AnywhereFlightBookMemberForm, self).__init__(*args, **kwargs)

        self.fields['member'].label_from_instance = lambda obj: "%s" % obj.get_full_name()



class FlightBookMemberConfirmForm(forms.Form):
    """
    A form to be used when confirming a member's reservation on a flight
    with the option to add companions
    """

    companions =  forms.ModelMultipleChoiceField(queryset=UserProfile.objects.none(), widget=forms.CheckboxSelectMultiple, required=False)

    def __init__(self, member, *args, **kwargs):
        super(FlightBookMemberConfirmForm, self).__init__(*args, **kwargs)

        perm = Permission.objects.get(codename='can_fly')
        # companions = User.objects.filter(Q(groups__permissions=perm) | Q(user_permissions=perm), is_active=True, account=member.account).distinct().exclude(pk=member.pk)
        companions_ids = User.objects.filter(Q(groups__permissions=perm) | Q(user_permissions=perm), is_active=True, account=member.account).distinct().exclude(pk=member.pk).values_list("id",flat=True)
        companions = UserProfile.objects.filter(Q(user__id__in=companions_ids) | ((Q(user__isnull=True) & Q(account=member.account)))).exclude(pk=member.pk).distinct()
        self.fields['companions'].queryset = companions

class FlightBookMemberCancelForm(forms.Form):
    cancellation_reason = forms.CharField(max_length=50)


class FlightBookMemberPayForm(forms.Form):
    """
    A form to be used when selecting a member for booking on a flight
    """
    class OverrideChoices:
        YES = '1'
        NO = '0'

    OVERRIDE_CHOICES = (
        (OverrideChoices.YES, 'Yes'),
        (OverrideChoices.NO, 'No')
    )
    override_charge =  forms.ChoiceField(choices=OVERRIDE_CHOICES, initial=OverrideChoices.NO, widget=forms.RadioSelect, error_messages={'required': 'Confirm payment choice.'})

class AnywhereFlightEditForm(forms.Form):

    origin = forms.ModelChoiceField(queryset=None, empty_label="Origin Airport",
        error_messages={'required': 'Origin Airport is required.'})

    destination = forms.ModelChoiceField(queryset=None,empty_label="Destination Airport",
       error_messages={'required': 'Destination Airport is required.'})

    plane = forms.ModelChoiceField(Plane.objects.all(), empty_label="Select Plane", required=True,
                                   error_messages={'required': 'Plane is required.'})
    start_date = forms.DateField(widget=forms.DateInput(format="%m/%d/%Y", attrs={'placeholder': 'MM / DD / YEAR'}),
         label="Start Date", error_messages={'required': 'Start Date is required.'})
    takeoff_time = forms.TimeField(widget=forms.TimeInput(format="%H:%M", attrs={'placeholder': '00:00'}),
         label='Takeoff Time', error_messages={'required': 'Takeoff time is required.'})
    # # TimeInput will work for duration as long as durations are under 24 hours, which they should always be
    # # given the business model here.
    #
    duration = forms.TimeField(widget=forms.TimeInput(format="%H:%M", attrs={'placeholder': '00:00'}), label="Duration",
         error_messages={'required': 'Duration length is required.'})
    pilot = UserModelChoiceField(User.objects.filter(groups__name='Pilot'), empty_label="Pilot Name", required=False)
    copilot = UserModelChoiceField(User.objects.filter(groups__name='Pilot'), empty_label="Co-Pilot Name", required=False)
    flight_number = forms.CharField(widget=forms.TextInput(attrs={'placeholder': 'Flight Number'}), max_length=16,
         required=True, error_messages={'required': 'Flight Number is required.'})
    sharing = forms.ChoiceField(choices=const.SHARING_CHOICES)

    full_flight_cost = forms.DecimalField(decimal_places=2, error_messages={'required': 'Full flight cost is required.'})
    other_cost = forms.DecimalField(decimal_places=2, required=False)
    other_cost_desc = forms.CharField(widget=forms.TextInput(attrs={'placeholder':'Other Cost Description'}),max_length=100, required=False)

    class Meta:
        fields = ('origin','destination','duration', 'sharing','plane', 'pilot', 'copilot','flight_number', 'full_flight_cost',
                  'other_cost','other_cost_desc', 'start_date','takeoff_time')

    def __init__(self, *args, **kwargs):

        instance = kwargs.pop('instance', None)
        initial = kwargs.pop('initial')
        object_data = {}
        if instance is None:
            # if we didn't get an instance, instantiate a new one - should never happen!
            self.instance = Flight()
        else:
            self.instance = instance
            object_data['origin'] = instance.origin
            object_data['destination'] = instance.destination
            object_data['plane'] = instance.plane
            object_data['duration'] = instance.duration_as_time()
            object_data['start_date'] = instance.departure.astimezone(pytz.timezone(instance.origin.timezone)).date()
            object_data['takeoff_time'] = instance.departure.astimezone(pytz.timezone(instance.origin.timezone)).timetz()
            object_data['pilot'] = instance.pilot
            object_data['copilot'] = instance.copilot
            object_data['flight_number'] = instance.flight_number
            object_data['sharing'] = instance.anywhere_details.sharing
            object_data['full_flight_cost'] = instance.anywhere_details.full_flight_cost
            object_data['other_cost'] = instance.anywhere_details.other_cost
            object_data['other_cost_desc'] = instance.anywhere_details.other_cost_desc

        if initial:
            object_data.update(initial)

        super(AnywhereFlightEditForm, self).__init__(initial=object_data, *args, **kwargs)
        origin_list = []
        destination_list =[]
        route_list = AnywhereRoute.objects.all()
        for id in route_list:
            origin_list.append(id.origin_id)
        for id in route_list:
            destination_list.append(id.destination_id)
        airports = Airport.objects.filter(Q(id__in=origin_list) | Q(id__in=destination_list)).all()
        self.fields['origin'].queryset = airports
        self.fields['destination'].queryset = airports

    def save_flight(self, created_by, seats_to_confirm):
        flight = self.instance
        details = flight.anywhere_details

        flight.origin = self.cleaned_data.get('origin')
        flight.destination = self.cleaned_data.get('destination')
        flight.flight_number = self.cleaned_data.get('flight_number')
        flight.plane = self.cleaned_data.get('plane')
        flight.pilot = self.cleaned_data.get('pilot')
        flight.copilot = self.cleaned_data.get('copilot')
        flight.flight_type = Flight.TYPE_ANYWHERE

        # take our start date and takeoff time and put them together
        tz = pytz.timezone(flight.origin.timezone)
        takeoff_at = self.cleaned_data.get('takeoff_time')

        departure_time = datetime.combine(self.cleaned_data.get('start_date'), takeoff_at)
        # workaround to get the time correct.  using .replace(tzinfo=XXXX) can get weird results due to dst stuff.
        # localize the naive datetime comes from http://stackoverflow.com/a/25390097
        departure_time = tz.localize(departure_time)
        flight.departure = departure_time.astimezone(pytz.UTC)

        # Convert duration as a time object to seconds from 00:00:00
        duration = self.cleaned_data.get('duration')
        duration_as_minutes = (duration.hour * 60) + duration.minute
        flight.duration = duration_as_minutes

        flight.arrival = flight.departure + timedelta(minutes=flight.duration)

        details.sharing = self.cleaned_data.get('sharing')
        details.full_flight_cost = self.cleaned_data.get('full_flight_cost')
        details.other_cost = self.cleaned_data.get('other_cost')
        details.other_cost_desc = self.cleaned_data.get('other_cost_desc')
        # AMF Fix calculation to use current cost.
        seats_booked = flight.seats_total - flight.seats_available
        if seats_booked >= seats_to_confirm:
            next_seat = seats_booked+1
        else:
            next_seat = seats_to_confirm
        details.per_seat_cost = details.full_flight_cost / next_seat

        details.save()

        flight.anywhere_details = details

        flight.save()

        return flight


class AnywhereFlightCreationForm(forms.Form):
    """
    Used to generate Flight from a leg in a FlightRequest and Route metadata
    Used in a WizardView either once or twice depending on if FlightSet is roundtrip or oneway
    """
    origin = forms.ModelChoiceField(queryset=None, empty_label="Origin Airport",
        error_messages={'required': 'Origin Airport is required.'})

    destination = forms.ModelChoiceField(queryset=None,empty_label="Destination Airport",
       error_messages={'required': 'Destination Airport is required.'})

    plane = forms.ModelChoiceField(Plane.objects.all(), empty_label="Select Plane", required=True,
                                   error_messages={'required': 'Plane is required.'})
    start_date = forms.DateField(widget=forms.DateInput(format="%m/%d/%Y", attrs={'placeholder': 'MM / DD / YEAR'}),
         label="Start Date", error_messages={'required': 'Start Date is required.'})
    takeoff_time = forms.TimeField(widget=forms.TimeInput(format="%H:%M", attrs={'placeholder': '00:00'}),
         label='Takeoff Time', error_messages={'required': 'Takeoff time is required.'})
    # # TimeInput will work for duration as long as durations are under 24 hours, which they should always be
    # # given the business model here.
    #
    duration = forms.TimeField(widget=forms.TimeInput(format="%H:%M", attrs={'placeholder': '00:00'}), label="Duration",
         error_messages={'required': 'Duration length is required.'})
    pilot = UserModelChoiceField(User.objects.filter(groups__name='Pilot'), empty_label="Pilot Name", required=False)
    copilot = UserModelChoiceField(User.objects.filter(groups__name='Pilot'), empty_label="Co-Pilot Name", required=False)
    flight_number = forms.CharField(widget=forms.TextInput(attrs={'placeholder': 'Flight Number'}), max_length=16,
         required=True, error_messages={'required': 'Flight Number is required.'})
    sharing = forms.ChoiceField(choices=const.SHARING_CHOICES)

    full_flight_cost = forms.DecimalField(decimal_places=2, error_messages={'required': 'Full flight cost is required.'})
    other_cost = forms.DecimalField(decimal_places=2, required=False)
    other_cost_desc = forms.CharField(widget=forms.TextInput(attrs={'placeholder':'Other Cost Description'}),max_length=100, required=False)
    total_legs = forms.IntegerField(min_value=1, max_value=2, widget=forms.HiddenInput)
    selected_seats = forms.IntegerField(widget=forms.HiddenInput)
    seats_required = forms.IntegerField(widget=forms.HiddenInput)

    class Meta:
        fields = ('origin','destination','duration', 'sharing','plane', 'pilot', 'copilot','flight_number', 'full_flight_cost',
                  'other_cost','other_cost_desc', 'start_date','takeoff_time','total_legs','selected_seats')

    def __init__(self, initial, *args, **kwargs):
        # initialize the form from the flight request & other passed in data
        depart_when = initial['depart_when']
        if depart_when == AnywhereFlightRequest.WHEN_MORNING:
            takeoff_time = settings.DEFAULT_MORNING_TAKEOFF
        elif depart_when == AnywhereFlightRequest.WHEN_AFTERNOON:
            takeoff_time = settings.DEFAULT_AFTERNOON_TAKEOFF
        elif depart_when == AnywhereFlightRequest.WHEN_EVENING:
            takeoff_time = settings.DEFAULT_EVENING_TAKEOFF
        else:
            takeoff_time = settings.DEFAULT_FLEXIBLE_TAKEOFF

        takeoff_time = datetime.strptime(takeoff_time, "%H:%M:%S")
        tz = pytz.timezone(initial["origin_city"].timezone)

        object_data = {
            'origin': initial['origin_city'],
            'destination': initial['destination_city'],
            'duration': initial['duration'],
            'start_date': initial['depart_date'],
            'takeoff_time': tz.localize(takeoff_time),
            'sharing': initial['sharing'],
            'full_flight_cost': initial['full_flight_cost'],
            'total_legs': initial['total_legs'],
            'selected_seats':initial['selected_seats'],
            'seats_required': initial['seats_required']
        }

        super(AnywhereFlightCreationForm, self).__init__(initial=object_data, *args, **kwargs)
        origin_list = []
        destination_list =[]
        route_list = AnywhereRoute.objects.all()
        for id in route_list:
            origin_list.append(id.origin_id)
        for id in route_list:
            destination_list.append(id.destination_id)
        airports = Airport.objects.filter(Q(id__in=origin_list) | Q(id__in=destination_list)).all()
        self.fields['origin'].queryset = airports
        self.fields['destination'].queryset = airports

    def clean_other_cost(self):
        other_cost = self.cleaned_data.get('other_cost')
        if other_cost is None:
            other_cost = 0
        return other_cost

    def clean(self, *args, **kwargs):
        cleaned_data = super(AnywhereFlightCreationForm, self).clean(*args, **kwargs)

        origin = cleaned_data.get('origin')
        destination = cleaned_data.get('destination')
        if origin == destination:
            raise forms.ValidationError("Flight cannot have the same origin and destination.")
        if cleaned_data.get('plane') is not None:
            if cleaned_data.get('plane').seats < cleaned_data.get('selected_seats'):
                raise forms.ValidationError("The selected plane does not have sufficient seats.")


        return cleaned_data

    def save(self, flight_request, created_by=None):
        """
        Saves an Anywhere Flight its AnywhereFlightDetails from FormData and AnywhereFlightRequest and returns the Flight.
        Args:
            flight_request: AnywhereFlightReqeust

        Returns:  Flight

        """
        flight = Flight()
        details = AnywhereFlightDetails()

        flight.origin=self.cleaned_data.get('origin')
        flight.destination=self.cleaned_data.get('destination')
        flight.flight_number=self.cleaned_data.get('flight_number')
        flight.plane=self.cleaned_data.get('plane')
        flight.pilot=self.cleaned_data.get('pilot')
        flight.copilot=self.cleaned_data.get('copilot')
        flight.flight_type='A'

        if created_by:
            flight.created_by=created_by


        flight.surcharge=0
        flight.corporate_max=0
        flight.companion_max=0

        #takeourstartdateandtakeofftimeandputthemtogether
        tz=pytz.timezone(flight.origin.timezone)
        takeoff_at=self.cleaned_data.get('takeoff_time')

        departure_time=datetime.combine(self.cleaned_data.get('start_date'),takeoff_at)
        #workaroundtogetthetimecorrect.using.replace(tzinfo=XXXX)cangetweirdresultsduetodststuff.
        #localizethenaivedatetimecomesfromhttp://stackoverflow.com/a/25390097
        departure_time=tz.localize(departure_time)
        flight.departure=departure_time.astimezone(pytz.UTC)

        #Convertdurationasatimeobjecttosecondsfrom00:00:00
        duration=self.cleaned_data.get('duration')
        duration_as_minutes=(duration.hour*60)+duration.minute
        flight.duration=duration_as_minutes

        flight.arrival=flight.departure+timedelta(minutes=flight.duration)

        flight.vip=False

        flight.founder=False

        flight.seats_total = flight.plane.seats
        flight.seats_available = flight.plane.seats
        flight.seats_companion = 0 #we don't use companion passes for Anywhere flights. Everyone pays the same.
        flight.max_seats_corporate = flight.plane.seats
        flight.max_seats_companion = 0

        details.anywhere_request = flight_request
        details.confirmation_status = 'NOTFULL'
        details.sharing = self.cleaned_data.get('sharing')
        details.full_flight_cost = self.cleaned_data.get('full_flight_cost')
        details.other_cost = self.cleaned_data.get('other_cost')
        details.other_cost_desc = self.cleaned_data.get('other_cost_desc')
        seats_required = self.cleaned_data.get('seats_required')
        # the initial per-seat cost is based on the seats_required selected by Flight Creator.
        # this may change in future.
        details.per_seat_cost = details.full_flight_cost / seats_required
        details.flight_creator_user = flight_request.created_by

        details.save()
        flight.anywhere_details = details

        flight.save()
        return flight


class AnywhereOutboundFlightCreationForm(AnywhereFlightCreationForm):
    leg = 1

class AnywhereReturnFlightCreationForm(AnywhereFlightCreationForm):
    leg = 2


class AdminAnywhereFlightCreationForm(forms.Form):
    """
    Used to generate Anywhere Flight manually by an admin
    """

    origin = forms.ModelChoiceField(queryset=None, empty_label="Origin Airport",
        error_messages={'required': 'Origin Airport is required.'})

    destination = forms.ModelChoiceField(queryset=None,empty_label="Destination Airport",
       error_messages={'required': 'Destination Airport is required.'})
    plane = forms.ModelChoiceField(Plane.objects.all(), empty_label="Select Plane", required=True,
                                   error_messages={'required': 'Plane is required.'})
    start_date = forms.DateField(widget=forms.DateInput(format="%m/%d/%Y", attrs={'placeholder': 'MM / DD / YEAR'}),
         label="Start Date", error_messages={'required': 'Start Date is required.'})
    takeoff_time = forms.TimeField(widget=forms.TimeInput(format="%H:%M", attrs={'placeholder': '00:00'}),
         label='Takeoff Time', error_messages={'required': 'Takeoff time is required.'})
    # # TimeInput will work for duration as long as durations are under 24 hours, which they should always be
    # # given the business model here.
    #
    duration = forms.TimeField(widget=forms.TimeInput(format="%H:%M", attrs={'placeholder': '00:00'}), label="Duration",
         error_messages={'required': 'Duration length is required.'})
    pilot = UserModelChoiceField(User.objects.filter(groups__name='Pilot'), empty_label="Pilot Name", required=False)
    copilot = UserModelChoiceField(User.objects.filter(groups__name='Pilot'), empty_label="Co-Pilot Name", required=False)
    flight_number = forms.CharField(widget=forms.TextInput(attrs={'placeholder': 'Flight Number'}), max_length=16,
         required=True, error_messages={'required': 'Flight Number is required.'})
    sharing = forms.ChoiceField(choices=const.SHARING_CHOICES)

    full_flight_cost = forms.DecimalField(decimal_places=2, error_messages={'required': 'Full flight cost is required.'})
    other_cost = forms.DecimalField(decimal_places=2, required=False)
    other_cost_desc = forms.CharField(widget=forms.TextInput(attrs={'placeholder':'Other Cost Description'}),max_length=100, required=False)
    total_legs = forms.IntegerField(min_value=1, max_value=2, widget=forms.HiddenInput)
    selected_seats = forms.IntegerField()
    seats_required = forms.IntegerField()
    plannames = ['Express','Executive','Chairman','RISE ANYWHERE']
    planids = Plan.objects.filter(name__in=plannames).values_list('id', flat=True)
    userlist=User.objects.filter(account__plan__in=planids).all()

    flight_creator = UserModelChoiceField(userlist,empty_label="Flight Creator", required=False)
    class Meta:
        fields = ('origin','destination','duration', 'sharing','plane', 'pilot', 'copilot','flight_number', 'full_flight_cost',
                  'other_cost','other_cost_desc', 'start_date','takeoff_time','total_legs','selected_seats','seats_required','flight_creator')

    def __init__(self, initial, *args, **kwargs):
        # Since this is an admin form coming w/o flight request there are few defaults

        takeoff_time = settings.DEFAULT_FLEXIBLE_TAKEOFF

        takeoff_time = datetime.strptime(takeoff_time, "%H:%M:%S")

        object_data = {

            'takeoff_time':takeoff_time,
            'total_legs': initial['total_legs'],
            'selected_seats': initial['selected_seats']
        }

        super(AdminAnywhereFlightCreationForm, self).__init__(initial=object_data, *args, **kwargs)

        origin_list = []
        destination_list =[]
        route_list = AnywhereRoute.objects.all()
        for id in route_list:
            origin_list.append(id.origin_id)
        for id in route_list:
            destination_list.append(id.destination_id)
        airports = Airport.objects.filter(Q(id__in=origin_list) | Q(id__in=destination_list)).all()
        self.fields['origin'].queryset = airports
        self.fields['destination'].queryset = airports

    def clean_other_cost(self):
        other_cost = self.cleaned_data.get('other_cost')
        if other_cost is None:
            other_cost = 0
        return other_cost

    def clean(self, *args, **kwargs):
        cleaned_data = super(AdminAnywhereFlightCreationForm, self).clean(*args, **kwargs)

        origin = cleaned_data.get('origin')
        destination = cleaned_data.get('destination')

        if origin == destination:
            raise forms.ValidationError("Flight cannot have the same origin and destination.")

        if cleaned_data.get('plane') is not None:
            if cleaned_data.get('plane').seats < cleaned_data.get('seats_required'):
                raise forms.ValidationError("The selected plane does not have sufficient seats for the # of spots required to confirm.  Either choose a larger plane or lower spots required to confirm.")


        return cleaned_data

    def save(self, flight_request, created_by=None):
        """
        Saves an Anywhere Flight its AnywhereFlightDetails from FormData and AnywhereFlightRequest and returns the Flight.
        Args:
            flight_request: AnywhereFlightReqeust

        Returns:  Flight

        """
        flight = Flight()
        details = AnywhereFlightDetails()

        flight.origin=self.cleaned_data.get('origin')
        flight.destination=self.cleaned_data.get('destination')
        flight.flight_number=self.cleaned_data.get('flight_number')
        flight.plane=self.cleaned_data.get('plane')
        flight.pilot=self.cleaned_data.get('pilot')
        flight.copilot=self.cleaned_data.get('copilot')
        flight.flight_type='A'

        flight.created_by=created_by


        flight.surcharge=0
        flight.corporate_max=0
        flight.companion_max=0

        #takeourstartdateandtakeofftimeandputthemtogether
        tz=pytz.timezone(flight.origin.timezone)
        takeoff_at=self.cleaned_data.get('takeoff_time')

        departure_time=datetime.combine(self.cleaned_data.get('start_date'),takeoff_at)
        #workaroundtogetthetimecorrect.using.replace(tzinfo=XXXX)cangetweirdresultsduetodststuff.
        #localizethenaivedatetimecomesfromhttp://stackoverflow.com/a/25390097
        departure_time=tz.localize(departure_time)
        flight.departure=departure_time.astimezone(pytz.UTC)

        #Convertdurationasatimeobjecttosecondsfrom00:00:00
        duration=self.cleaned_data.get('duration')
        duration_as_minutes=(duration.hour*60)+duration.minute
        flight.duration=duration_as_minutes

        flight.arrival=flight.departure+timedelta(minutes=flight.duration)

        flight.vip=False

        flight.founder=False

        flight.seats_total = flight.plane.seats
        flight.seats_available = flight.plane.seats
        flight.seats_companion = 0 #we don't use companion passes for Anywhere flights. Everyone pays the same.
        flight.max_seats_corporate = flight.plane.seats
        flight.max_seats_companion = 0

        details.anywhere_request = flight_request
        details.confirmation_status = 'NOTFULL'
        details.sharing = self.cleaned_data.get('sharing')
        details.full_flight_cost = self.cleaned_data.get('full_flight_cost')
        details.other_cost = self.cleaned_data.get('other_cost')
        details.other_cost_desc = self.cleaned_data.get('other_cost_desc')
        seats_required = self.cleaned_data.get('seats_required')
        # the initial per-seat cost is based on the seats_required selected by Flight Creator.
        # this may change in future.
        details.per_seat_cost = details.full_flight_cost / seats_required

        details.flight_creator_user = flight_request.created_by

        details.save()
        flight.anywhere_details = details

        flight.save()

        return flight
