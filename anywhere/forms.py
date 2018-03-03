from django import forms

from anywhere.models import AnywhereFlightRequest,AnywhereRoute
from django.db.models.query_utils import Q
from flights.models import Airport


class AnywhereFlightRequestRouteForm(forms.ModelForm):
    """
    Form for initiating a Rise Anywhere flight booking.
    """
    seats = forms.ChoiceField(choices=((x+1, x+1) for x in range(AnywhereFlightRequest.MAX_SEATS)), required=True)
    is_round_trip = forms.ChoiceField(choices=((False, 'One way'), (True, 'Round trip')),widget=forms.RadioSelect())

    class Meta:
        model = AnywhereFlightRequest
        fields = (
            'seats','origin_city', 'destination_city',
            'is_round_trip',
        )
        labels = {
            'seats': 'How many are going?',
            'origin_city': 'From Where?',
            'destination_city': 'To Where?',
            'is_round_trip': 'Round Trip or One Way',
        }

    def __init__(self, *args, **kwargs):
        super(AnywhereFlightRequestRouteForm, self).__init__(*args, **kwargs)
        self.fields['origin_city'].empty_label = 'City'
        self.fields['destination_city'].empty_label = 'City'
        origin_list = []
        destination_list =[]
        route_list = AnywhereRoute.objects.all()
        for id in route_list:
            origin_list.append(id.origin_id)
        for id in route_list:
            destination_list.append(id.destination_id)
        airports = Airport.objects.filter(Q(id__in=origin_list) | Q(id__in=destination_list)).all()
        self.fields['origin_city'].queryset = airports
        self.fields['destination_city'].queryset = airports

    def clean(self):

        cleaned_data = super(AnywhereFlightRequestRouteForm, self).clean()

        origin_city = cleaned_data.get('origin_city')
        destination_city = cleaned_data.get('destination_city')
        is_round_trip = cleaned_data.get('is_round_trip')

        if is_round_trip is None:
            self._errors['is_round_trip'] = 'Please select one way or round trip'

        if origin_city is None:
            self._errors['origin_city'] = 'Please enter origin city'

        if destination_city is None:
            self._errors['destination_city'] = 'Please enter destination city'

        if origin_city == destination_city:
            raise forms.ValidationError("Flight cannot have the same origin and destination.")

        return cleaned_data


class AnywhereFlightRequestDatesForm(forms.ModelForm):
    class Meta:
        model = AnywhereFlightRequest
        fields = (
            'depart_date', 'depart_when',
            'return_date', 'return_when',
        )

        labels = {
            'depart_when': 'Time',
            'return_when': 'Time'
        }


class AnywhereFlightRequestPassengersForm(forms.ModelForm):
    class Meta:
        model = AnywhereFlightRequest
        fields = (
            'sharing', 'seats_required'
        )

class AnywhereUpgradeForm(forms.Form):
    cancellation = forms.BooleanField(required=True)
