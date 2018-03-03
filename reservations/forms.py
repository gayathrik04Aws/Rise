from django import forms
import datetime
from localflavor.us.forms import USPhoneNumberField

from .models import FlightReservation
from flights.models import Airport, Route, Flight
from accounts.models import User, UserProfile
from accounts.fields import AdvancedModelMultipleChoiceField, AdvancedModelChoiceField
from django.db.models.query_utils import Q

class AirportForm(forms.Form):
    """
    A form to choose an airport
    """

    airport = AdvancedModelChoiceField(queryset=Airport.objects.all(), empty_label=None)

    def __init__(self, *args, **kwargs):
        super(AirportForm, self).__init__(*args, **kwargs)
        now = datetime.datetime.now
        # RISE-340 Can't pull from route list because it has past routes and one-offs.  Need only future flights, origins only
        # since this dropdown is "where would you like to fly FROM."
        idlist = Flight.objects.filter(departure__gt=now).exclude(flight_type='A').values_list("origin_id", flat=True).distinct()
        airports = Airport.objects.filter(Q(id__in=idlist)).distinct()


        # route_list = Route.objects.all()
        # origin_list = []
        # destination_list =[]
        # for id in route_list:
        #     origin_list.append(id.origin_id)
        # for id in route_list:
        #     destination_list.append(id.destination_id)
        # airports = Airport.objects.filter(Q(id__in=origin_list) | Q(id__in=destination_list)).all()
        self.fields["airport"].queryset = airports


class CancelReservationForm(forms.Form):
    """
    A form for canceling a reservation
    """
    reservation_id = forms.IntegerField(error_messages={'required': 'Reservation ID is required.'})

    class Meta:
        model = FlightReservation
        fields = ('id')

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        super(CancelReservationForm, self).__init__(*args, **kwargs)


class CompanionCountForm(forms.Form):
    """
    A form to capture companion count
    """
    COMPANION_CHOICES = (
        (0, 'No. of Companions'),
        (1, '1 companion'),
        (2, '2 companions'),
        (3, '3 companions'),
    )
    companion_count = forms.ChoiceField(choices=COMPANION_CHOICES, initial=1)
    companions_only = forms.BooleanField(initial=False, label="I will NOT be flying on this booking",widget=forms.CheckboxInput, required=False)

    def clean(self):
        companion_count = self.cleaned_data.get("companion_count")
        if "companions_only" in self.cleaned_data:
            companions_only = self.cleaned_data.get("companions_only")
            if companions_only == True and int(companion_count) == 0:
                self.add_error("companions_only", "You must have at least one companion flying if you are not.")

        return self.cleaned_data



class FilterResultsForm(forms.Form):
    """
    A form to filter flight results
    """
    FILTER_CHOICES = (
        ('', 'Filter Results'),
        ('all-flights', 'All Flights'),
        ('seats-available', 'Seats Available'),
        ('promotional-flight', 'Promotional Flights'),
        ('fun-flight', 'Fun Flights'),
    )
    filters = forms.ChoiceField(choices=FILTER_CHOICES)


class CompanionSelectionForm(forms.Form):
    """
    A form to choose companion(s) for a flight
    """

    companions = AdvancedModelMultipleChoiceField(queryset=UserProfile.objects.none(), widget=forms.CheckboxSelectMultiple, error_messages={'required': 'Please select companions.'})

    def __init__(self, account, count, *args, **kwargs):
        """
        account: account to get the list of companions from
        count: the number of companions to choose
        """
        super(CompanionSelectionForm, self).__init__(*args, **kwargs)

        self.count = count

        self.fields['companions'].queryset = account.get_companion_profiles()

    def clean_companions(self):
        companions = self.cleaned_data.get('companions')

        if len(companions) != self.count:
            if self.count == 1:
                self.add_error('companions', 'Please choose only %d companion' % self.count)
            else:
                self.add_error('companions', 'Please choose only %d companions' % self.count)

        return companions


class AddCompanionForm(forms.Form):
    """
    A form for adding a companion user to the current Account
    """
    first_name = forms.CharField(max_length=30, error_messages={'required': 'First name is required.'})
    last_name = forms.CharField(max_length=30, error_messages={'required': 'Last name is required.'})
    email = forms.EmailField(error_messages={'required': 'Email address is required.'})
    phone = USPhoneNumberField(error_messages={'required': 'Phone number is required.'})
    mobile_phone = USPhoneNumberField(required=False, error_messages={})
    date_of_birth = forms.DateField(widget=forms.DateInput(format='%m/%d/%Y'), input_formats=('%m/%d/%Y', '%m/%d/%y',), error_messages={'required': 'Date of Birth is required.'})
    weight = forms.ChoiceField(widget=forms.Select, choices=UserProfile.WEIGHT_RANGE_CHOICES)

    def __init__(self, count, *args, **kwargs):
        self.account = kwargs.pop('account')
        super(AddCompanionForm, self).__init__(*args, **kwargs)
        self.count = count

    def clean_email(self):
        """
        Check to see if this email already belongs to someone else.
        """
        email = self.cleaned_data.get('email')

        if User.objects.filter(email=email).exists():
            self._errors['email'] = self.error_class(['This email has already been used.'])

        return email


class SimplePaymentForm(forms.Form):
    """
    A simple payment form for collecting the stripe token
    """

    payment_method_nonce = forms.CharField(required=False)

    nickname = forms.CharField(max_length=20,required=False,widget=forms.TextInput(attrs={'placeholder': 'Nickname'}))


