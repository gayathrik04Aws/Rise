from django import forms

from datetime import datetime, timedelta
import pytz
import arrow

from accounts.models import User
from .models import Announcement,AutomatedMessage

class AnnouncementForm(forms.ModelForm):
    """
    A form for creating an announcement
    """
    message = forms.CharField(max_length=60, required=True, error_messages={'required': 'Message is required.'}, widget=forms.TextInput())
    link_name = forms.CharField(max_length=60, required=False, widget=forms.TextInput())

    class Meta:
        model = Announcement
        fields = ('title','message','link_name', 'link')

    def clean(self):
        link = self.cleaned_data.get('link')
        link_name = self.cleaned_data.get('link_name')

        if link and not link_name:
            self.add_error('link_name', 'Name for link is required.')

        if link_name and not link:
            self.add_error('link', 'Please add a link URL.')


class AnnouncementListForm(forms.Form):
    message_key = forms.ChoiceField(choices = AutomatedMessage.MESSAGE_KEY_CHOICES)
    sms_text = forms.CharField(required=False,max_length=160)
    email_text = forms.CharField(required=False,max_length=500, widget=forms.Textarea)
    message_box_text = forms.CharField(required=False, max_length=500, widget=forms.Textarea)
    substitution_info = forms.CharField(required=False, max_length=500)
