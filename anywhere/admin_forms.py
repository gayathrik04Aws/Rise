from django import forms
from django.conf import settings

from anywhere import models
from flights.models import Flight
import arrow
from core.tasks import send_html_email_task


class AnywhereFlightRequestActionForm(forms.Form):
    ACTION_APPROVE = 'approve'
    ACTION_DECLINE = 'decline'
    ACTION_MESSAGE = 'message'

    ACTION_CHOICES = (
        (ACTION_APPROVE, 'Approve Flight Request'),
        (ACTION_DECLINE, 'Decline Flight Request'),
        (ACTION_MESSAGE, 'Send Message')
    )

    target = forms.ModelChoiceField(queryset=models.ANYWHERE_PENDING_QUERYSET)
    action = forms.ChoiceField(choices=ACTION_CHOICES)


class AnywhereFlightSetActionForm(forms.Form):
    FLIGHTSET_ACTION_CONFIRM = 'confirm'
    FLIGHTSET_ACTION_MESSAGE = 'message'
    FLIGHTSET_ACTION_CHOICES = (
        (FLIGHTSET_ACTION_CONFIRM, 'Confirm Flight Set'),
        (FLIGHTSET_ACTION_MESSAGE, 'Send Message')
    )

    flightset_action = forms.ChoiceField(choices=FLIGHTSET_ACTION_CHOICES)
    flightset = forms.ModelChoiceField(queryset=models.AnywhereFlightSet.get_anywhere_ready_queryset())


class AnywhereFlightSetUnconfirmedActionForm(AnywhereFlightSetActionForm):
    flightset = forms.ModelChoiceField(queryset=models.AnywhereFlightSet.get_anywhere_unconfirmed_queryset())


class AnywhereFlightRequestSendMessageForm(forms.Form):
    RECIPIENT_ALL = 'all'
    RECIPIENT_CREATOR = 'creator'

    RECIPIENT_CHOICES = (
        (RECIPIENT_ALL, 'All Passengers'),
        (RECIPIENT_CREATOR, 'Flight Creator'),
    )

    flight_request = forms.ModelChoiceField(queryset=models.AnywhereFlightRequest.objects, widget=forms.HiddenInput)
    recipients = forms.ChoiceField(choices=RECIPIENT_CHOICES)
    title = forms.CharField(max_length=80, initial='Message about your Rise Anywhere Flight')
    message = forms.CharField(widget=forms.Textarea)

    def get_recipients(self):
        """
        Calculate which emails th is message should be sent to.

        :return: a list of email addresses
        """
        freq = self.cleaned_data['flight_request']

        if self.cleaned_data['recipients'] == AnywhereFlightRequestSendMessageForm.RECIPIENT_ALL:
            fs = models.AnywhereFlightSet.objects.filter(anywhere_request=freq).first()
            if fs is None:
                return [freq.created_by.email]

            return [p.email for p in fs.passenger_query.all()]
        elif self.cleaned_data['recipients'] == AnywhereFlightRequestSendMessageForm.RECIPIENT_CREATOR:
            return [freq.created_by.email]
        else:
            raise NotImplemented("Recipient type {} not implemented".format(self.cleaned_data['recipients']))

    def send(self):
        freq = self.cleaned_data['flight_request']
        context = freq.email_context

        flight_set = models.AnywhereFlightSet.objects.filter(anywhere_request=freq).first()

        if flight_set is not None:
            departing_flight = Flight.objects.filter(id = flight_set.leg1_id).first()
            context.update({
                'leg1' : departing_flight
            })

        if flight_set is not None and flight_set.leg2_id is not None:
            return_flight = Flight.objects.filter(id = flight_set.leg2_id).first()
            context.update({
                'leg2' : return_flight
            })

        context.update({
            'title': self.cleaned_data['title'],
            'message': self.cleaned_data['message'],
        })

        recipients = self.get_recipients()

        # send one at a time?
        for email in recipients:
            send_html_email_task.delay(
                'emails/anywhere_message',
                context,
                self.cleaned_data['title'],
                settings.DEFAULT_FROM_EMAIL,
                [email],
            )


class AnywhereRouteListForm(forms.Form):
    route_list = forms.ModelMultipleChoiceField(queryset=models.AnywhereRoute.objects.all(), widget=forms.CheckboxSelectMultiple, error_messages={'required': 'No routes were selected.'})



class AnywhereRouteForm(forms.ModelForm):

    duration = forms.TimeField(widget=forms.TimeInput(format='%H:%M', attrs={'placeholder': '00:00'}), error_messages={'required': 'Duration is required in format H:MM.'})

    class Meta:
        model = models.AnywhereRoute
        fields = ('name', 'origin', 'destination', 'duration','cost',)

    def __init__(self, *args, **kwargs):
        super(AnywhereRouteForm, self).__init__(*args, **kwargs)
        if self.instance.duration:
            self.initial['duration'] = self.instance.duration_as_timedelta()

        self.fields['name'].error_messages = {'required': 'Route name is required.'}
        self.fields['origin'].empty_label = None
        self.fields['destination'].empty_label = None
        self.fields['cost'].error_messages = {'required': 'Cost is required.'}

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
