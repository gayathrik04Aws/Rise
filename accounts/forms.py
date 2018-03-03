from django import forms
from django.forms.formsets import formset_factory
from django.contrib.auth.forms import SetPasswordForm, AuthenticationForm, PasswordChangeForm, PasswordResetForm
from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.db.models import Q

import re
from htmlmailer.mailer import send_html_email
from localflavor.us.forms import USPhoneNumberField, USZipCodeField
from localflavor.us.us_states import STATE_CHOICES

from billing.models import Plan, Card, BankAccount, PlanContractPrice
from .models import City, User, Account
from .fields import AdvancedModelChoiceField


class LandingForm(forms.Form):
    """
    Simple form for signing up for notifications
    """

    first_name = forms.CharField(max_length=30, error_messages={'required': 'First name is required.'})
    last_name = forms.CharField(max_length=30, error_messages={'required': 'Last name is required.'})
    email = forms.EmailField(error_messages={'required': 'Email address is required.'})


class NotifyForm(forms.Form):
    """
    Simple form for signing up for notifications
    """

    first_name = forms.CharField(max_length=30, error_messages={'required': 'First name is required.'})
    last_name = forms.CharField(max_length=30, error_messages={'required': 'Last name is required.'})
    email = forms.EmailField()
    preferred_cities = forms.ModelMultipleChoiceField(queryset=City.objects.all(), widget=forms.CheckboxSelectMultiple, required=False)


class NotifyWaitlistForm(forms.Form):
    """
    Simple form for signing up for waitlist
    """

    first_name = forms.CharField(max_length=30, error_messages={'required': 'First name is required.'})
    last_name = forms.CharField(max_length=30, error_messages={'required': 'Last name is required.'})
    email = forms.EmailField(error_messages={'required': 'Email is required.'})
    city = forms.CharField(error_messages={'required': 'City is required.'})


class SignUpForm(forms.Form):
    """
    Form to enter initial sign-up contact information, city, and invitation code
    """

    first_name = forms.CharField(max_length=30, error_messages={'required': 'First name is required.'})
    last_name = forms.CharField(max_length=30, error_messages={'required': 'Last name is required.'})
    email = forms.EmailField(error_messages={'required': 'Email address is required.'})
    phone = USPhoneNumberField(error_messages={'required': 'Phone number is required.'})
    origin_city = forms.ModelChoiceField(queryset=City.objects.all(), widget=forms.RadioSelect, required=False, empty_label=None)
    code = forms.CharField(max_length=32, required=False)
    other_city_checkbox = forms.BooleanField(required=False)
    write_in_city = forms.CharField(max_length=100, required=False)

    def clean(self):
        """
        Ensure that we have either an origin_city or a write_in_city
        """
        cleaned_data = super(SignUpForm, self).clean()

        origin_city = cleaned_data.get('origin_city')
        other_city_checkbox = cleaned_data.get('other_city_checkbox')
        write_in_city = cleaned_data.get('write_in_city')

        if other_city_checkbox and not write_in_city:
            self._errors['write_in_city'] = 'Please enter your own origin city'
            raise forms.ValidationError('Please enter your own origin city')

        if not origin_city and not write_in_city:
            raise forms.ValidationError('Please select an origin city or enter your own')

        return cleaned_data

    def clean_email(self):
        """
        Check to see if this email is already signed up.
        """
        email = self.cleaned_data.get('email')

        if User.objects.filter(email=email).exists():
            self._errors['email'] = self.error_class(['This email has already been used.'])

        return email

    def clean_write_in_city(self):
        """
        Strips any whitespace off the ends of write_in_city
        """
        write_in_city = self.cleaned_data.get('write_in_city', '')
        return write_in_city.strip()

class AnywhereBasicSignUpForm(forms.Form):
    """
    Form to enter initial sign-up contact information, city for a person invited through a Rise Anywhere flight
    """

    first_name = forms.CharField(max_length=30, error_messages={'required': 'First name is required.'})
    last_name = forms.CharField(max_length=30, error_messages={'required': 'Last name is required.'})
    email = forms.EmailField(error_messages={'required': 'Email address is required.'})
    phone = USPhoneNumberField(error_messages={'required': 'Phone number is required.'})
    origin_city = forms.ModelChoiceField(queryset=City.objects.all(), widget=forms.RadioSelect, required=False, empty_label=None)
    other_city_checkbox = forms.BooleanField(required=False)
    write_in_city = forms.CharField(max_length=100, required=False)
    terms = forms.BooleanField(required=True, error_messages={'required': 'Agree to the site\'s terms and conditions to continue.'})
    #removed
    #monarch_air_terms = forms.BooleanField(required=True, error_messages={'required': 'Agree to Monarch Air\'s terms and conditions to continue.'})
    mailchimp = forms.BooleanField(required=False, initial=True)

    def clean(self):
        """
        X -- Ensure that we have either an origin_city or a write_in_city
        Currently RiseAnywhere doesn't capture the origin city as it's not relevant
        """
        cleaned_data = super(AnywhereBasicSignUpForm, self).clean()

        # origin_city = cleaned_data.get('origin_city')
        # other_city_checkbox = cleaned_data.get('other_city_checkbox')
        # write_in_city = cleaned_data.get('write_in_city')
        #
        # if other_city_checkbox and not write_in_city:
        #     self._errors['write_in_city'] = 'Please enter your own origin city'
        #     raise forms.ValidationError('Please enter your own origin city')
        #
        # if not origin_city and not write_in_city:
        #     raise forms.ValidationError('Please select an origin city or enter your own')

        return cleaned_data

    def clean_email(self):
        """
        Check to see if this email is already signed up.
        """
        email = self.cleaned_data.get('email')

        if User.objects.filter(email=email).exists():
            self._errors['email'] = self.error_class(['This email has already been used.'])

        return email

    # def clean_write_in_city(self):
    #     """
    #     Strips any whitespace off the ends of write_in_city
    #     """
    #     write_in_city = self.cleaned_data.get('write_in_city', '')
    #     return write_in_city.strip()


class CorporateSignUpForm(forms.Form):
    """
    Form to enter initial sign-up contact information for a company account
    """

    first_name = forms.CharField(max_length=30, error_messages={'required': 'First name is required.'})
    last_name = forms.CharField(max_length=30, error_messages={'required': 'Last name is required.'})
    email = forms.EmailField(error_messages={'required': 'Email address is required.'})
    company = forms.CharField(max_length=30, error_messages={'required': 'Company name is required.'})
    phone = USPhoneNumberField(required=False, error_messages={})

    def clean_email(self):
        """
        Check to see if this email is already signed up.
        """
        email = self.cleaned_data.get('email')
        no_no_list = (
            'aol.com',
            'hotmail.com',
            'gmail.com',
            'yahoo.com'
        )
        no_no_re = re.compile('|.+'.join(no_no_list))

        if re.search(no_no_re, email):
            self._errors['email'] = self.error_class(['Please enter your company email address.'])

        if User.objects.filter(email=email).exists():
            self._errors['email'] = self.error_class(['This email has already been used.'])

        return email


class CorporateSignUpConfirmForm(forms.Form):
    """
    Form to enter initial sign-up contact information for a company account
    """

    first_name = forms.CharField(max_length=30, error_messages={'required': 'First name is required.'})
    last_name = forms.CharField(max_length=30, error_messages={'required': 'Last name is required.'})
    email = forms.EmailField(error_messages={'required': 'Email address is required.'})
    company = forms.CharField(max_length=30, error_messages={'required': 'Company name is required.'})
    phone = USPhoneNumberField(error_messages={'required': 'Phone number is required.'})
    member_count = forms.IntegerField(initial=2, error_messages={'required': 'Member count is required.'})
    pass_count = forms.IntegerField(initial=2, error_messages={'required': 'Pass count is required.'})

    def clean_member_count(self):
        count = self.cleaned_data.get('member_count')

        if count < 2:
            self.add_error('member_count', 'Corporate accounts require at least 2 members')

        return count

    def clean_email(self):
        email = self.cleaned_data.get('email')

        if User.objects.filter(email=email).exists():
            self.add_error('email', 'A user with that email already exists')

        return email

    def clean_pass_count(self):
        count = self.cleaned_data.get('pass_count')

        if count < 2:
            self.add_error('pass_count', 'Corporate accounts require at least 2 legs')

        if count % 2 == 1:
            self.add_error('pass_count', 'Legs must be in multiples of 2')

        return count


class CorporatePaymentForm(forms.Form):
    """
    """

    token = forms.CharField(required=False, error_messages={'required': 'Payment token is required.'})
    payment_method = forms.ChoiceField(choices=(('ACH', 'Bank Account'), ('Card', 'Credit Card'), ('Manual', 'Wire or Check')), widget=forms.RadioSelect, error_messages={'required': 'Please select payment information.'})
    nickname = forms.CharField(max_length=20,required=False,widget=forms.TextInput(attrs={'placeholder': 'Nickname'}))
    background_check = forms.BooleanField(required=False)
    approve_membership_agreement = forms.BooleanField(error_messages={'required': 'Please approve the Membership Agreement to continue.'})
    terms = forms.BooleanField(required=True, error_messages={'required': 'Agree to the site\'s terms and conditions to continue.'})
    # monarch_air_terms = forms.BooleanField(required=True, error_messages={'required': 'Agree to Monarch Air\'s terms and conditions to continue.'})

    def clean(self):
        data = self.cleaned_data

        payment_method = data.get('payment_method')
        token = data.get('token')

        if payment_method in ('ACH', 'Card') and not token:
            self.add_error('payment_method', 'Payment information required.')

        return data


class SignUpPaymentForm(forms.Form):
    """
    Initial sign up payment form
    """

    first_name = forms.CharField(max_length=30, error_messages={'required': 'First name is required.'})
    last_name = forms.CharField(max_length=30, error_messages={'required': 'Last name is required.'})
    email = forms.EmailField(error_messages={'required': 'Email address is required.'})
    phone = USPhoneNumberField(error_messages={'required': 'Phone number is required.'})
    token = forms.CharField(error_messages={'required': 'Payment token is required.'})
    background_check = forms.BooleanField(required=False)
    terms = forms.BooleanField(required=True, error_messages={'required': 'Agree to the site\'s terms and conditions to continue.'})
    #monarch_air_terms = forms.BooleanField(required=True, error_messages={'required': 'Agree to Monarch Air\'s terms and conditions to continue.'})
    mailchimp = forms.BooleanField(required=False, initial=True)
    preferred_cities = forms.ModelMultipleChoiceField(queryset=City.objects.all(), widget=forms.CheckboxSelectMultiple, required=False)
    shipping_same = forms.BooleanField(required=False, initial=True)

    payment_method = forms.ChoiceField(choices=(('ACH', 'Bank Account'), ('Card', 'Credit Card')), widget=forms.RadioSelect)
    nickname = forms.CharField(max_length=20,required=False,widget=forms.TextInput(attrs={'placeholder': 'Nickname'}))

    bill_street_1 = forms.CharField(max_length=128, error_messages={'required': 'Billing street address is required.'})
    bill_street_2 = forms.CharField(max_length=128, required=False)
    bill_city = forms.CharField(max_length=64, error_messages={'required': 'Billing city is required.'})
    bill_state = forms.ChoiceField(required=True, choices=STATE_CHOICES, initial='TX')
    bill_postal_code = USZipCodeField(error_messages={'required': 'Billing zip code is required.'})

    ship_street_1 = forms.CharField(max_length=128, required=False)
    ship_street_2 = forms.CharField(max_length=128, required=False)
    ship_city = forms.CharField(max_length=64, required=False)
    ship_state = forms.ChoiceField(required=False, choices=STATE_CHOICES, initial='TX')
    ship_postal_code = USZipCodeField(required=False)

    def clean_email(self):
        """
        Check to see if this email is already signed up.
        """
        email = self.cleaned_data.get('email')

        if User.objects.filter(email=email).exists():
            self._errors['email'] = self.error_class(['This email has already been used.'])

        return email

    def clean(self):
        """
        If the shipping address is not the same, set fields to required and run validators again
        """
        data = self.cleaned_data

        if not data.get('shipping_same'):
            if not data.get('ship_street_1'):
                self._errors['ship_street_1'] = self.error_class(['Shipping street address required.'])

            if not data.get('ship_city'):
                self._errors['ship_city'] = self.error_class(['Shipping city is required.'])

            if not data.get('ship_state'):
                self._errors['ship_state'] = self.error_class(['Shipping state is required.'])

            if not data.get('ship_postal_code'):
                self._errors['ship_postal_code'] = self.error_class(['Shipping zip code is required.'])

        return data

class SignUpPaymentAnywhereForm(forms.Form):
    """
    Initial sign up payment form
    """

    first_name = forms.CharField(max_length=30, error_messages={'required': 'First name is required.'})
    last_name = forms.CharField(max_length=30, error_messages={'required': 'Last name is required.'})
    email = forms.EmailField(error_messages={'required': 'Email address is required.'})
    phone = USPhoneNumberField(error_messages={'required': 'Phone number is required.'})
    token = forms.CharField(error_messages={'required': 'Payment token is required.'})
    background_check = forms.BooleanField(required=False)
    nickname = forms.CharField(max_length=20,required=False,widget=forms.TextInput(attrs={'placeholder': 'Nickname'}))
    # terms = forms.BooleanField(required=True, error_messages={'required': 'Agree to the site\'s terms and conditions to continue.'})
    # monarch_air_terms = forms.BooleanField(required=True, error_messages={'required': 'Agree to Monarch Air\'s terms and conditions to continue.'})
    # mailchimp = forms.BooleanField(required=False, initial=True)
    preferred_cities = forms.ModelMultipleChoiceField(queryset=City.objects.all(), widget=forms.CheckboxSelectMultiple, required=False)
    shipping_same = forms.BooleanField(required=False, initial=True)

    payment_method = forms.ChoiceField(choices=(('ACH', 'Bank Account'), ('Card', 'Credit Card')), widget=forms.RadioSelect)

    bill_street_1 = forms.CharField(max_length=128, error_messages={'required': 'Billing street address is required.'})
    bill_street_2 = forms.CharField(max_length=128, required=False)
    bill_city = forms.CharField(max_length=64, error_messages={'required': 'Billing city is required.'})
    bill_state = forms.ChoiceField(required=True, choices=STATE_CHOICES, initial='TX')
    bill_postal_code = USZipCodeField(error_messages={'required': 'Billing zip code is required.'})

    ship_street_1 = forms.CharField(max_length=128, required=False)
    ship_street_2 = forms.CharField(max_length=128, required=False)
    ship_city = forms.CharField(max_length=64, required=False)
    ship_state = forms.ChoiceField(required=False, choices=STATE_CHOICES, initial='TX')
    ship_postal_code = USZipCodeField(required=False)

    def clean(self):
        """
        If the shipping address is not the same, set fields to required and run validators again
        """
        data = self.cleaned_data

        if not data.get('shipping_same'):
            if not data.get('ship_street_1'):
                self._errors['ship_street_1'] = self.error_class(['Shipping street address required.'])

            if not data.get('ship_city'):
                self._errors['ship_city'] = self.error_class(['Shipping city is required.'])

            if not data.get('ship_state'):
                self._errors['ship_state'] = self.error_class(['Shipping state is required.'])

            if not data.get('ship_postal_code'):
                self._errors['ship_postal_code'] = self.error_class(['Shipping zip code is required.'])

        return data

class RegisterAccountForm(SetPasswordForm):
    """
    Form for begining the on-boarding registration

    SetPasswordForm
    ---------------
    new_password1: User's new password
    new_password2: Confirm user's new password

    date_of_birth: User's date of birth
    approve_background_check: Required checkbox to approve background check
    """

    date_of_birth = forms.DateField(widget=forms.DateInput(format='%m/%d/%Y'), input_formats=('%m/%d/%Y', '%m/%d/%y'), error_messages={'required': 'Date of birth is required.', 'invalid': 'Please enter your date of birth in the MM/DD/YYYY format.'})
    approve_membership_agreement = forms.BooleanField(error_messages={'required': 'Please approve the Membership Agreement'})
    approve_background_check = forms.BooleanField(error_messages={'required': 'Please approve the Terms and Conditions'})
    approve_carriage_contract = forms.BooleanField(error_messages={'required': 'Please approve the Contract of Carriage'})
    contract_signature = forms.CharField(max_length=50, error_messages = {'required': 'Enter your name in the Signature field.'})
    contract_signdate = forms.DateField(widget=forms.DateInput(format='%m/%d/%Y'), input_formats=('%m/%d/%Y', '%m/%d/%y'), error_messages = {'required': 'Enter the current date in the Date field.'})

    # contract contains both membership + plan info.  But trials don't have contracts.
    member_plan = AdvancedModelChoiceField(queryset=Plan.objects.filter(active=True, anywhere_only=False), empty_label=None, widget=forms.RadioSelect, required=False)
    contract = AdvancedModelChoiceField(queryset=PlanContractPrice.objects.filter(selectable=True), empty_label=None, widget=forms.RadioSelect, required=False)
    company_name = forms.CharField(max_length=128)

    def clean_pass_count(self):
        count = self.cleaned_data.get('pass_count')

        if count % 2 != 0:
            self.add_error('pass_count', 'Must have an even number of save my seat passes.')

        return count

    def clean(self):
        # make sure if they have a plan requiring a contract they have a contract selected and have signed
        data = self.cleaned_data
        plan = data.get('member_plan')
        contract = data.get('contract')

        if plan:
            if plan.requires_contract:
                if not contract:
                    self.add_error('contract', 'The plan you have selected requires a contract.')
        # if they have a contract but no plan, set the plan.  Since plan boxes will be hidden.
        if contract:
            data["member_plan"] = contract.plan;
        return data


    def __init__(self, user, *args, **kwargs):
        """
        Based on account type, remove unused fields
        """
        super(RegisterAccountForm, self).__init__(user, *args, **kwargs)

        self.fields['date_of_birth'].widget.attrs.update({'placeholder': 'MM/DD/YYYY'})

        self.fields['new_password1'].widget.attrs.update({'placeholder': 'Create Password'})
        self.fields['new_password2'].widget.attrs.update({'placeholder': 'Re-type Password'})
        self.fields['new_password1'].error_messages.update({'required': 'Password is required.'})
        self.fields['new_password2'].error_messages.update({'required': 'Please confirm your new password.'})

        if user.account.account_type == Account.TYPE_CORPORATE:
            del self.fields['member_plan']
            del self.fields['contract']
        else:
            # if the user is already setup with a trial plan, allow it (not all 0 amt plans are trials anymore!)
            if user.account.plan and user.account.plan.amount == 0 and user.account.plan.anywhere_only == False:
                self.fields['member_plan'].queryset = Plan.objects.filter(Q(active=True) | (Q(amount=0) & Q(anywhere_only=False))).order_by('amount')
            del self.fields['company_name']


class RegisterAnywhereBasicAccountForm(SetPasswordForm):
    """
    Form for begining the on-boarding registration

    SetPasswordForm
    ---------------
    new_password1: User's new password
    new_password2: Confirm user's new password

    date_of_birth: User's date of birth
    approve_background_check: Required checkbox to approve background check
    """

    date_of_birth = forms.DateField(widget=forms.DateInput(format='%m/%d/%Y'), input_formats=('%m/%d/%Y', '%m/%d/%y'), error_messages={'required': 'Date of birth is required.', 'invalid': 'Please enter your date of birth in the MM/DD/YYYY format.'})
    approve_membership_agreement = forms.BooleanField(error_messages={'required': 'Please approve the Membership Agreement'})
    approve_background_check = forms.BooleanField(error_messages={'required': 'Please approve the Terms and Conditions'})
    approve_carriage_contract = forms.BooleanField(error_messages={'required': 'Please approve the Contract of Carriage'})

    #RA or RA Ltd
    member_plan = AdvancedModelChoiceField(queryset=Plan.objects.filter(active=True, anywhere_only=True), empty_label=None, widget=forms.RadioSelect, error_messages={'required': 'A membership level is required.'})

    #No company name for RA
    #company_name = forms.CharField(max_length=128)

    def clean_pass_count(self):
        count = self.cleaned_data.get('pass_count')

        if count % 2 != 0:
            self.add_error('pass_count', 'Must have an even number of save my seat passes.')

        return count

    def __init__(self, user, *args, **kwargs):
        """
        Based on account type, remove unused fields
        """
        super(RegisterAnywhereBasicAccountForm, self).__init__(user, *args, **kwargs)

        self.fields['date_of_birth'].widget.attrs.update({'placeholder': 'MM/DD/YYYY'})

        self.fields['new_password1'].widget.attrs.update({'placeholder': 'Create Password'})
        self.fields['new_password2'].widget.attrs.update({'placeholder': 'Re-type Password'})
        self.fields['new_password1'].error_messages.update({'required': 'Password is required.'})
        self.fields['new_password2'].error_messages.update({'required': 'Please confirm your new password.'})


class RegisterPaymentForm(forms.Form):
    """
    Registration payment form.

    Allows a user to continue using their existing card if they have one.
    Allows a user to enter a new credit card
    Allows a corporate account user to setup a manual payment process.
    """

    payment_choice = forms.ChoiceField(widget=forms.RadioSelect, error_messages={'required': 'Please choose a payment method.'})
    nickname = forms.CharField(max_length=20,required=False,widget=forms.TextInput(attrs={'placeholder': 'Nickname'}))
    token = forms.CharField(required=False, error_messages={'required': 'Payment token is required.'})
    payment_method_nonce = forms.CharField(required=False, error_messages={'required': 'Payment token is required.'})
    bill_street_1 = forms.CharField(max_length=128, required=False, error_messages={'required': 'Billing street address is required.'})
    bill_street_2 = forms.CharField(max_length=128, required=False)
    bill_city = forms.CharField(max_length=64, required=False, error_messages={'required': 'Billing city is required.'})
    bill_state = forms.ChoiceField(choices=STATE_CHOICES, initial='TX', required=False)
    bill_postal_code = USZipCodeField(required=False, error_messages={'required': 'Billing zip code is required.'})

    def __init__(self, user, *args, **kwargs):
        """
        Dyanmic payment choices. If they have a card, allow them to use it. Anyone can add a new card.
        If corporate account, allow manual payment.
        """
        super(RegisterPaymentForm, self).__init__(*args, **kwargs)

        choices = []
        if Card.objects.filter(account=user.account).exists():
            choices.append(('existing_card', 'Use saved card'))

        if BankAccount.objects.filter(account=user.account).exists():
            choices.append(('existing_ach', 'Use saved bank account'))

        choices.append(('new', 'Credit Card'))

        choices.append(('ach', 'Bank Account'))

        choices.append(('manual', 'Pay by other Pre-Arranged Method'))

        self.fields['payment_choice'].choices = choices
        self.fields['bill_city'].widget.attrs.update({'placeholder': 'City'})
        self.fields['bill_street_1'].widget.attrs.update({'placeholder': 'Street Address'})
        self.fields['bill_street_2'].widget.attrs.update({'placeholder': 'Street Address (optional)'})
        self.fields['bill_postal_code'].widget.attrs.update({'placeholder': 'Zip Code'})

    def clean(self):
        """
        Require token and billing fields if new payment method is choosen
        """
        data = self.cleaned_data

        payment_choice = data.get('payment_choice')

        if payment_choice == 'new':
            if not data.get('payment_method_nonce'):
                self.add_error('payment_method_nonce', 'Payment token is required')
        if payment_choice == 'ach':
            if not data.get('token'):
                self.add_error('token', 'Payment token is required')
        if payment_choice in ('ach', 'new'):
            if not data.get('bill_street_1'):
                self.add_error('bill_street_1', 'Billing street address is required')
            if not data.get('bill_city'):
                self.add_error('bill_city', 'Billing city is required')
            if not data.get('bill_state'):
                self.add_error('bill_state', 'Billing state is required')
            if not data.get('bill_postal_code'):
                self.add_error('bill_postal_code', 'Billing zip code is required')

        return data


class ChangePlanForm(forms.Form):
    """
    A form to allow a user to choose a new plan
    """

    member_plan = AdvancedModelChoiceField(queryset=Plan.objects.filter(active=True).order_by('amount'), empty_label=None, widget=forms.RadioSelect)
    contract = AdvancedModelChoiceField(queryset=PlanContractPrice.objects.all(),empty_label=None, widget=forms.RadioSelect, required=False)

    def __init__(self, *args, **kwargs):
        super(ChangePlanForm, self).__init__(*args, **kwargs)
        initial = kwargs.pop('initial', None)
        data = kwargs.pop('data', None)
        if data and 'member_plan' in data:
            self.fields['contract'].queryset = PlanContractPrice.objects.filter(plan_id=data['member_plan']).order_by('contract_length')
        elif initial['member_plan']:
            self.fields['contract'].queryset = PlanContractPrice.objects.filter(plan_id=initial['member_plan'].id).order_by('contract_length')

    def clean_contract(self):
        contractid = self.data.get('contract')
        contract = PlanContractPrice.objects.filter(id=contractid).first()
        return contract

class LoginForm(AuthenticationForm):
    """
    Update existing authentication form to have placeholders
    """

    def __init__(self, request=None, *args, **kwargs):
        super(LoginForm, self).__init__(request, *args, **kwargs)

        self.fields['username'].widget.attrs.update({'placeholder': 'Email address or username', 'autofocus': '', 'autocorrect': 'off', 'autocapitalize': 'off'})
        self.fields['username'].error_messages.update({'required': 'Email address is required.'})

        self.fields['password'].widget.attrs.update({'placeholder': 'Password'})
        self.fields['password'].error_messages.update({'required': 'Password is required.'})

        self.error_messages['invalid_login'] = 'Oops! That email address and password combination didn\'t work.'


class PasswordChangeForm(PasswordChangeForm):
    """
    Update existing password change form to have placeholders
    """

    def __init__(self, *args, **kwargs):
        super(PasswordChangeForm, self).__init__(*args, **kwargs)

        self.fields['old_password'].widget.attrs.update({'placeholder': 'Old password', 'autofocus': ''})
        self.fields['old_password'].error_messages.update({'required': 'Old password is required.'})

        self.fields['new_password1'].widget.attrs.update({'placeholder': 'New password'})
        self.fields['new_password1'].error_messages.update({'required': 'New password is required.'})

        self.fields['new_password2'].widget.attrs.update({'placeholder': 'Confirm new password'})
        self.fields['new_password2'].error_messages.update({'required': 'Please confirm your new password.'})


class PasswordResetForm(PasswordResetForm):

    def __init__(self, *args, **kwargs):
        super(PasswordResetForm, self).__init__(*args, **kwargs)

        self.fields['email'].widget.attrs.update({'placeholder': 'Email address', 'autofocus': ''})
        self.fields['email'].error_messages.update({'required': 'Email address is required.'})

    def save(self, *args, **kwargs):
        """
        Generates a one-use only link for resetting password and sends to the
        user.
        """
        email = self.cleaned_data['email']
        users = User.objects.filter(email__iexact=email, is_active=True)

        for curr_user in users:
            # Make sure that no email is sent to a user that actually has
            # a password marked as unusable
            if not curr_user.has_usable_password():
                continue

            context = {
                'email': curr_user.email,
                'uid': urlsafe_base64_encode(force_bytes(curr_user.pk)),
                'user': curr_user,
                'token': default_token_generator.make_token(curr_user),
            }
            subject = 'Rise Password Reset'

            send_html_email('emails/password_reset', context, subject, settings.DEFAULT_FROM_EMAIL, [curr_user.email])


class SetPasswordForm(SetPasswordForm):

    def __init__(self, *args, **kwargs):
        super(SetPasswordForm, self).__init__(*args, **kwargs)

        self.fields['new_password1'].widget.attrs.update({'placeholder': 'New password', 'autofocus': ''})
        self.fields['new_password1'].error_messages.update({'required': 'New password is required.'})

        self.fields['new_password2'].widget.attrs.update({'placeholder': 'Confirm new password'})
        self.fields['new_password2'].error_messages.update({'required': 'Please confirm your new password.'})


class MemberWelcomeForm(SetPasswordForm):
    """
    Extend the set password form to also include date of birth and T&C approvals
    """

    date_of_birth = forms.DateField(widget=forms.DateInput(format='%m/%d/%Y', attrs={'placeholder': 'Date of Birth'}), input_formats=('%m/%d/%Y', '%m/%d/%y'), error_messages={'required': 'Date of birth is required.', 'invalid': 'Please enter your date of birth in the MM/DD/YYYY format.'})
    approve_membership_agreement = forms.BooleanField(error_messages={'required': 'Please approve the Membership Agreement'})
    approve_background_check = forms.BooleanField(error_messages={'required': 'Please approve the Terms and Conditions'})
    approve_carriage_contract = forms.BooleanField(error_messages={'required': 'Please approve the Contract of Carriage'})


class PriceCalculatorForm(forms.Form):
    """
    Simple form for calcuating membership levels
    """

    num_members = forms.CharField(max_length=30, error_messages={'required': 'Number of members is required.'})
    num_seats = forms.CharField(max_length=30, error_messages={'required': 'Number of seats is required.'})


class ReferralInformationForm(forms.Form):
    """
    Form for sending information on who sent referral(s) to Rise
    """

    your_name = forms.CharField(max_length=30, error_messages={'required': 'Your name is required.'})
    your_email = forms.EmailField(error_messages={'required': 'Your is required.'})


class ReferralForm(forms.Form):
    """
    Form for a referral
    """
    name = forms.CharField(max_length=30, error_messages={'required': 'Referral name is required.'})
    email = forms.EmailField(error_messages={'required': 'Referral email is required.'})
    phone = forms.CharField(max_length=30, error_messages={'required': 'Referral phone number is required.'})


ReferralFormSet = formset_factory(ReferralForm)
