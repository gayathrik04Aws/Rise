from django import forms
from django.contrib.auth.models import Group
from django.core.validators import validate_email

from localflavor.us.forms import USPhoneNumberField, USZipCodeField
from localflavor.us.us_states import STATE_CHOICES

from accounts.models import User, UserProfile, Address, FoodOption, BillingPaymentMethod
from accounts.fields import AdvancedModelChoiceField
from flights.models import Airport


class ProfileForm(forms.Form):
    """
    A form for a user to update their basic profile information
    """

    first_name = forms.CharField(max_length=30, error_messages={'required': 'First name is required.'})
    last_name = forms.CharField(max_length=30, error_messages={'required': 'Last name is required.'})
    email = forms.EmailField(error_messages={'required': 'Email address is required.'})
    company_name = forms.CharField(max_length=120, required=False, error_messages={})
    phone = USPhoneNumberField(error_messages={'required': 'Phone number is required.'})
    mobile_phone = USPhoneNumberField(required=False, error_messages={})

    ship_street_1 = forms.CharField(max_length=128, required=False)
    ship_street_2 = forms.CharField(max_length=128, required=False)
    ship_city = forms.CharField(max_length=64, required=False)
    ship_state = forms.ChoiceField(required=False, choices=STATE_CHOICES, initial='TX')
    ship_postal_code = USZipCodeField(required=False)

    date_of_birth = forms.DateField(widget=forms.DateInput(format='%m/%d/%Y'), input_formats=('%m/%d/%Y', '%m/%d/%y',), error_messages={'required': 'Date of Birth is required.'})
    weight = forms.ChoiceField(widget=forms.Select, choices=UserProfile.WEIGHT_RANGE_CHOICES)

    origin_airport = AdvancedModelChoiceField(queryset=Airport.objects.all(), widget=forms.RadioSelect, required=False, empty_label=None)

    food_options = forms.ModelMultipleChoiceField(queryset=FoodOption.objects.all(), widget=forms.CheckboxSelectMultiple, required=False)
    allergies = forms.CharField(max_length=128, required=False)

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        super(ProfileForm, self).__init__(*args, **kwargs)

    def clean_email(self):
        """
        Check to see if this email already belongs to someone else.
        """
        email = self.cleaned_data.get('email')

        if User.objects.filter(email=email).exclude(id=self.user.id).exists():
            self._errors['email'] = self.error_class(['This email has already been used.'])

        return email


class AvatarForm(forms.ModelForm):
    """
    A form for a user to update their avatar
    """

    avatar = forms.ImageField(error_messages={'required': 'Profile image is required.'})

    class Meta:
        model = User
        fields = ('avatar',)


class BillingUpdateForm(forms.ModelForm):
    """
    A form to accept a credit card updates
    """

    payment_method_nonce = forms.CharField(required=True, error_messages={'required': 'Payment token is required.'})

    nickname = forms.CharField(max_length=20,required=False,widget=forms.TextInput(attrs={'placeholder': 'Nickname'}))
    is_default = forms.BooleanField(label="Make this payment default", required=False,
        widget=forms.CheckboxInput())
    street_1 = forms.CharField(max_length=128, required=False, error_messages={'required': 'Billing street address is required.'}, widget=forms.TextInput(attrs={'placeholder': 'Street Address 1'}))
    street_2 = forms.CharField(max_length=128, required=False, widget=forms.TextInput(attrs={'placeholder': 'Street Address 2'}))
    city = forms.CharField(max_length=64, required=False, error_messages={'required': 'Billing city is required.'}, widget=forms.TextInput(attrs={'placeholder': 'City'}))
    state = forms.ChoiceField(required=False, choices=STATE_CHOICES, initial='TX')
    postal_code = USZipCodeField(required=False, error_messages={'required': 'Billing zip code is required.'}, widget=forms.TextInput(attrs={'placeholder': 'Billing Zip Code'}))

    class Meta:
        model = Address
        fields = ('street_1', 'street_2', 'city', 'state', 'postal_code')


class BankAccountForm(forms.Form):
    """
    A simple payment form for collecting the stripe token
    Had to add routing and acct last 4 so we can handle scenario where they are adding
    an account that already exists.
    """

    token = forms.CharField()
    nickname = forms.CharField(max_length=20,required=False,widget=forms.TextInput(attrs={'placeholder': 'Nickname'}))
    routing = forms.CharField()
    last4 = forms.CharField()

class BankAccountVerifyForm(forms.Form):
    """
    A form to enter the 2 micro transaction verification value
    """

    verify_1 = forms.DecimalField(min_value=0.00, max_value=1, max_digits=3, decimal_places=2, error_messages={'required': 'Verification Amount 1 is required.'})
    verify_2 = forms.DecimalField(min_value=0.00, max_value=1, max_digits=3, decimal_places=2, error_messages={'required': 'Verification Amount 2 is required.'})


class SendInvitationForm(forms.Form):
    """
    A form for a user to send a new invite to a third party of their choice
    """

    first_name = forms.CharField(error_messages={'required': 'First name is required.'})
    last_name = forms.CharField(error_messages={'required': 'Last name is required.'})
    email = forms.EmailField(error_messages={'required': 'Email address is required.'})


class NotificationsForm(forms.ModelForm):
    """
    A form for updating a user's notification preferences
    """

    class Meta:
        model = UserProfile
        fields = ('alert_flight_email', 'alert_flight_sms', 'alert_promo_email', 'alert_promo_sms', 'alert_billing_email', 'alert_billing_sms',)


class CompanionForm(forms.ModelForm):
    """
    A form to add and edit companions
    """

    phone = USPhoneNumberField(error_messages={'required': 'Phone number is required.'})
    mobile_phone = USPhoneNumberField(required=False)
    date_of_birth = forms.DateField(widget=forms.DateInput(format='%m/%d/%Y', attrs={'placeholder': 'MM/DD/YEAR'}), input_formats=('%m/%d/%Y', '%m/%d/%y',), error_messages={'required': 'Date of Birth is required.'})
    weight = forms.ChoiceField(widget=forms.Select, choices=UserProfile.WEIGHT_RANGE_CHOICES, error_messages={'required': 'Weight is required.'})

    class Meta:
        model = UserProfile
        fields = ('first_name', 'last_name', 'email', 'phone', 'mobile_phone','weight', 'date_of_birth')

    def __init__(self, user,  *args, **kwargs):
        self.userprofile = user
        initial = kwargs.get('initial')
        if initial.get('account'):
            self.account = initial['account']
        if self.userprofile:
              initial.update({
                 'phone': self.userprofile.phone,
                 'mobile_phone': self.userprofile.mobile_phone,
                 'date_of_birth': self.userprofile.date_of_birth,
                 'weight': self.userprofile.weight,
             })

        super(CompanionForm, self).__init__(*args, **kwargs)

    def clean_email(self):
        """
        Check to see if this email already belongs to someone else.
        """
        email = self.cleaned_data.get('email')

        if self.userprofile and UserProfile.objects.filter(email=email).exclude(id=self.userprofile.id).exists():
            self._errors['email'] = self.error_class(['This email has already been used.'])

        return email

    def save(self):
        #user = super(CompanionForm, self).save()
        userprofile = super(CompanionForm, self).save()
        if not userprofile.account and self.account:
            userprofile.account = self.account
            userprofile.save()
        #try:
        #    user_profile = user.userprofile
        #except:
        #    user_profile = UserProfile(first_name=user.first_name, last_name=user.last_name, email=user.email, account=acct, user=user)

        # data = self.cleaned_data
        #
        # user_profile.phone = data.get('phone')
        # user_profile.mobile_phone = data.get('mobile_phone')
        # user_profile.date_of_birth = data.get('date_of_birth')
        # user_profile.weight = data.get('weight')
        # user_profile.save()

        try:
            user = userprofile.user
            user.first_name = userprofile.first_name
            user.last_name = userprofile.last_name
            user.email = userprofile.email
        except:
            user = User(userprofile=userprofile, first_name=userprofile.first_name, last_name=userprofile.last_name, email=userprofile.email, account=self.account)

        user.save()

        return userprofile


class AddEditMemberForm(forms.Form):
    """
    A form for adding a member user to the current Account
    """
    first_name = forms.CharField(max_length=30, error_messages={'required': 'First name is required.'})
    last_name = forms.CharField(max_length=30, error_messages={'required': 'Last name is required.'})
    email = forms.EmailField(error_messages={'required': 'Email address is required.'})

    phone = USPhoneNumberField(error_messages={'required': 'Phone number is required.'})
    mobile_phone = USPhoneNumberField(required=False, error_messages={})

    date_of_birth = forms.DateField(widget=forms.DateInput(format='%m/%d/%Y'), input_formats=('%m/%d/%Y', '%m/%d/%y',), error_messages={'required': 'Date of Birth is required.'})
    weight = forms.ChoiceField(widget=forms.Select, choices=UserProfile.WEIGHT_RANGE_CHOICES)

    ship_street_1 = forms.CharField(max_length=128, required=False)
    ship_street_2 = forms.CharField(max_length=128, required=False)
    ship_city = forms.CharField(max_length=64, required=False)
    ship_state = forms.ChoiceField(required=False, choices=STATE_CHOICES, initial='TX')
    ship_postal_code = USZipCodeField(required=False)

    member_groups = forms.ModelMultipleChoiceField(queryset=Group.objects.filter(name__in=['Corporate Account Admin', 'Coordinator', 'Account Member']), widget=forms.CheckboxSelectMultiple)
    payment_method = forms.ChoiceField(required=False, choices=(),initial='')


    def __init__(self, user, *args, **kwargs):
        super(AddEditMemberForm, self).__init__(*args, **kwargs)
        self.user = user
        pms = user.account.get_all_payment_methods()
        payment_choices = []
        for pm in pms:
           if pm['nickname'] is not None:
               txt = pm['text'] + " (" + pm['nickname'] + ")"
           else:
               txt = pm['text']
           payment_choices.append( (pm['id'], txt))

        self.fields['payment_method'].choices = payment_choices

    def clean_email(self):
        """
        Check to see if this email already belongs to someone else.
        """
        email = self.cleaned_data.get('email')

        if User.objects.filter(email=email).exclude(id=self.user.id).exists():
            self._errors['email'] = self.error_class(['This email has already been used.'])

        return email

    def clean_payment_methods(self):
        groups = self.cleaned_data.get('member_groups')
        payment_method = self.cleaned_data.get('payment_method')
        notcoord = groups.exclude(name='Coordinator').first()
        if notcoord and not payment_method:
            self._errors['payment_method'] = self.error_class(['You must select a payment method.'])

        return payment_method

class FilterMemberForm(forms.Form):
    """
    A form for choosing a team member to filter by
    """
    member_filters = forms.ChoiceField(choices=(), initial='')

    def __init__(self, account, *args, **kwargs):
        super(FilterMemberForm, self).__init__(*args, **kwargs)

        member_choices = [
            ('', 'Member'),
            ('all', 'All Members'),
        ]
        for member in User.objects.filter(account=account):
            member_choices.append((member.pk, member.get_full_name()))
        self.fields['member_filters'].choices = member_choices


class FilterReservationsForm(forms.Form):
    """
    A form for choosing reservation attributes to filter by
    """
    reservation_filters = forms.ChoiceField(choices=(), initial='')

    def __init__(self, account, *args, **kwargs):
        super(FilterReservationsForm, self).__init__(*args, **kwargs)

        if account.is_corporate():
            reservation_choices = [
                ('', 'Sort'),
                ('all-flights', 'All Flights'),
                ('complete-flights', 'Past Flights'),
                ('upcoming-flights', 'Upcoming Flights'),
                ('alpha-last-name-flights', 'A-Z by Last Name'),
                ('reverse-alpha-last-name-flights', 'Z-A by Last Name'),
                ('fun-flights', 'Fun Flights'),
                ('promotional-flights', 'Promotional Flights'),
            ]
        else:
            reservation_choices = [
                ('', 'Sort'),
                ('all-flights', 'All Flights'),
                ('complete-flights', 'Past Flights'),
                ('upcoming-flights', 'Upcoming Flights'),
                ('fun-flights', 'Fun Flights'),
                ('promotional-flights', 'Promotional Flights'),
            ]

        self.fields['reservation_filters'].choices = reservation_choices


class MultiEmailField(forms.Field):
    def to_python(self, value):
        """
        Normalize data to a list of strings.
        """
        # Return an empty list if no input was given.
        if not value:
            return []
        return [v.strip() for v in value.split(',')]

    def validate(self, value):
        """
        Check if value consists only of valid emails.
        """
        # Use the parent's handling of required fields, etc.
        super(MultiEmailField, self).validate(value)

        for email in value:
            validate_email(email)


class ReservationEmailForm(forms.Form):

    emails = MultiEmailField()
