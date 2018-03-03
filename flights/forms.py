from django import forms

from datetime import datetime, timedelta
import pytz

from accounts.models import User, Account
from billing.models import Plan

from .models import FlightFeedback, Airport, Plane, Flight, FlightPlanRestriction, Route, RouteTime


class FlightFeedbackForm(forms.ModelForm):
    """
    A form for providing feedback on a flight
    """
    rating = forms.IntegerField(error_messages={'required': 'Rating is required.'})
    comment = forms.CharField(max_length=1024, required=False)

    class Meta:
        model = FlightFeedback
        fields = ('rating', 'comment','flight')

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        super(FlightFeedbackForm, self).__init__(*args, **kwargs)
