from django import forms


class BookWithoutPaymentForm(forms.Form):
    """
    Form to specify whether to book a reservation which requires payment
    even though there has not been a payment when booking a flight from
    the waitlist.
    """

    force_booking = forms.BooleanField(required=False)
