from django import forms
from django.core import validators
from django.contrib.auth.models import Group
from django.contrib.auth.forms import UserCreationForm, UserChangeForm

from localflavor.us.forms import USPhoneNumberField, USZipCodeField
from localflavor.us.us_states import STATE_CHOICES

from .models import Account, User, UserNote, UserProfile, FoodOption,OncallSchedule, Address
from .fields import AdvancedModelChoiceField
from billing.models import Charge, PlanContractPrice, Plan
from flights.models import Airport,Route
from django.conf import settings


class AccountForm(forms.ModelForm):
    """
    A form for creating an account in the admin
    """

    class Meta:
        model = Account
        fields = ('founder', 'vip', 'status', 'plan', 'company_name', 'account_type', 'corporate_amount',
                  'payment_method', 'member_count', 'pass_count', 'companion_pass_count', 'primary_profile',
                  'onboarding_fee_paid', 'complimentary_passes', 'complimentary_companion_passes','do_not_charge','contract','do_not_renew')

    def __init__(self, user, *args, **kwargs):
        super(AccountForm, self).__init__(*args, **kwargs)
        self.user = user

        if not user.has_perm('accounts.can_edit_account_status'):
            del self.fields['status']

        if self.instance.id:
            self.fields['primary_profile'].queryset = UserProfile.objects.filter(account=self.instance)
            self.fields['primary_profile'].empty_label = None
            if self.instance.plan:
                contracts = PlanContractPrice.objects.filter(plan_id=self.instance.plan.id).all()
                choicelist = []
                for contract in contracts:
                    val = [contract.id, contract.__str__()]
                    choicelist.append(val)
                self.fields['contract'].choices = choicelist
            else:
                if self.instance.account_type == Account.TYPE_INDIVIDUAL:
                    #default to express, get express plans
                    plan = Plan.objects.filter(name='Express').first()
                    self.instance.plan = plan
                    contracts = PlanContractPrice.objects.filter(plan_id=plan.id).all()
                    choicelist = []
                    for contract in contracts:
                        val = [contract.id, contract.__str__()]
                        choicelist.append(val)
                        #default to the 12 month contract
                        if contract.contract_length == 12:
                            self.instance.contract = contract
                            self.initial['contract'] = contract

                    self.fields['contract'].choices = choicelist
                else:
                    #default to executive.
                    plan = Plan.objects.filter(name='Executive').first()
                    self.instance.plan = plan
                    #no corp contracts yet.

            # cancelled is no longer a choice to change status if the plan is a contract plan.
            if self.instance.status != Account.STATUS_CANCELLED:
                if self.instance.plan:
                    if self.instance.plan.requires_contract and self.instance.account_type == Account.TYPE_INDIVIDUAL :
                        choices = self.fields['status'].choices
                        choices.remove(('C', 'Cancelled'))
                        self.fields['status'].choices = choices


        else:
            del self.fields['primary_profile']
            if 'status' in self.fields:
                del self.fields['status']
            # see what default plan is and if it has contracts
            actualplan = self.initial['plan']
            contracts = PlanContractPrice.objects.filter(plan_id=actualplan.id).all()
            choicelist = []
            for contract in contracts:
                val = [contract.id, contract.__str__()]
                choicelist.append(val)
            self.fields['contract'].choices = choicelist

        self.fields['plan'].empty_label = None

    def clean(self):
        cleaned_data = super(AccountForm, self).clean()
        status = cleaned_data.get('status')
        account_type = cleaned_data.get('account_type')
        company_name = cleaned_data.get('company_name')

        if account_type == Account.TYPE_CORPORATE:
            if not company_name:
                self.add_error('company_name', 'Company name required for corporate accounts')

        if self.instance.id and not self.instance.is_manual() and self.instance.get_monthly_amount() > 0 and status == Account.STATUS_ACTIVE:
            card = self.instance.get_credit_card()
            bank = self.instance.get_bank_account()

            if card is None and bank is None:
                self.add_error('status', 'Cannot activate account with no payment method')

            if bank is not None and card is None and self.instance.need_verify_bank_account():
                self.add_error('status', 'Bank account needs verified before activating account')

        return cleaned_data


class StaffUserProfileForm(forms.Form):
    """
    A form for creating an account user in the admin
    """
    first_name = forms.CharField(max_length=30)
    last_name = forms.CharField(max_length=30)
    email = forms.EmailField()

    groups = forms.ModelMultipleChoiceField(queryset=Group.objects.none(), widget=forms.CheckboxSelectMultiple, required=False)

    phone = USPhoneNumberField(required=False)
    mobile_phone = USPhoneNumberField(required=False, error_messages={})

    ship_street_1 = forms.CharField(max_length=128, required=False)
    ship_street_2 = forms.CharField(max_length=128, required=False)
    ship_city = forms.CharField(max_length=64, required=False)
    ship_state = forms.ChoiceField(required=False, choices=STATE_CHOICES, initial='TX')
    ship_postal_code = USZipCodeField(required=False)

    date_of_birth = forms.DateField(widget=forms.DateInput(format='%m/%d/%Y'), input_formats=('%m/%d/%Y', '%m/%d/%y',), required=False)
    weight = forms.ChoiceField(widget=forms.Select, choices=UserProfile.WEIGHT_RANGE_CHOICES)

    origin_airport = AdvancedModelChoiceField(queryset=Airport.objects.all(), widget=forms.RadioSelect, required=False, empty_label=None)

    food_options = forms.ModelMultipleChoiceField(queryset=FoodOption.objects.all(), widget=forms.CheckboxSelectMultiple, required=False)
    allergies = forms.CharField(max_length=128, required=False)

    account = forms.ModelChoiceField(queryset=Account.objects.filter(account_type=Account.TYPE_CORPORATE), widget=forms.Select, required=True, empty_label='--------')

    class Meta:
        #model = User
        fields = ('first_name', 'last_name', 'phone', 'mobile_phone', 'date_of_birth', 'weight', 'origin_airport','food_options','allergies', 'email','groups', 'account')

    def __init__(self, *args, **kwargs):
        super(StaffUserProfileForm, self).__init__(*args, **kwargs)

        # 16 = Pilot
        # 17 = Co-Pilot
        # 18 = Concierge
        # 19 = Operations
        #  1 = Admin
        groups = Group.objects.filter(name__in=['Pilot', 'Co-Pilot', 'Concierge', 'Operations', 'Admin', 'Monarch', 'Account Member'])
        initial = None

        self.fields['groups'].queryset = groups
        self.fields['groups'].initial = initial

    def clean_groups(self):
        mygroups = self.cleaned_data.get('groups')
        ids = []
        if mygroups:
            for group in mygroups:
                ids.append(group.id)
        if ids.__len__() > 0:
            list = Group.objects.filter(id__in=ids).all()
        else:
            list = {}

        return list

    def save(self, profile=None):
        if profile is None:
            profile = UserProfile()
        profile.first_name = self.cleaned_data.get("first_name")
        profile.last_name = self.cleaned_data.get("last_name")
        profile.email = self.cleaned_data.get("email")
        profile.phone = self.cleaned_data.get("phone")
        profile.mobile_phone = self.cleaned_data.get("mobile_phone")
        profile.date_of_birth = self.cleaned_data.get("date_of_birth")
        profile.weight = self.cleaned_data.get("weight")
        profile.allergies = self.cleaned_data.get("allergies")
        #profile.food_options = self.cleaned_data.get("food_options")
        profile.origin_airport = self.cleaned_data.get("origin_airport")
        profile.account = self.cleaned_data.get("account")
        profile.save()

        if profile.shipping_address is None:
            profile.shipping_address = Address()
        profile.shipping_address.street_1 = self.cleaned_data.get("ship_street_1")
        profile.shipping_address.street_2 = self.cleaned_data.get("ship_street_2")
        profile.shipping_address.city = self.cleaned_data.get("ship_city")
        profile.shipping_address.state= self.cleaned_data.get("ship_state")
        profile.shipping_address.postal_code = self.cleaned_data.get("ship_postal_code")
        profile.shipping_address.save()
        profile.shipping_address_id = profile.shipping_address.id

        try:
             user = profile.user
        except:
             user = User(userprofile=profile)

        profile.user = user
        profile.user.first_name = profile.first_name
        profile.user.last_name = profile.last_name
        profile.user.email = profile.email
        profile.user.account_id = profile.account.id
        profile.user.account = profile.account
        profile.user.save()

        profile.user.groups = self.cleaned_data.get("groups")

        profile.user.is_staff = True
        profile.user.is_active = True
        profile.user.save()

        profile.save()
        return profile


class UserProfileForm(forms.Form):
    """
    A form for creating an account's userprofile + user in the admin
    This is the new version where UserProfile is primary
    """
    first_name = forms.CharField(max_length=30)
    last_name = forms.CharField(max_length=30)
    email = forms.EmailField(required=False)
    groups = forms.ModelMultipleChoiceField(queryset=Group.objects.all(), widget=forms.CheckboxSelectMultiple, required=False)
    #groups = forms.MultipleChoiceField(widget=forms.CheckboxSelectMultiple, required=False)

    phone = USPhoneNumberField(required=False)
    mobile_phone = USPhoneNumberField(required=False, error_messages={})

    ship_street_1 = forms.CharField(max_length=128, required=False)
    ship_street_2 = forms.CharField(max_length=128, required=False)
    ship_city = forms.CharField(max_length=64, required=False)
    ship_state = forms.ChoiceField(required=False, choices=STATE_CHOICES, initial='TX')
    ship_postal_code = USZipCodeField(required=False)

    date_of_birth = forms.DateField(widget=forms.DateInput(format='%m/%d/%Y'), input_formats=('%m/%d/%Y', '%m/%d/%y',), required=False)
    weight = forms.ChoiceField(widget=forms.Select, choices=UserProfile.WEIGHT_RANGE_CHOICES)

    origin_airport = AdvancedModelChoiceField(queryset=Airport.objects.all(), widget=forms.RadioSelect, required=False, empty_label=None)

    food_options = forms.ModelMultipleChoiceField(queryset=FoodOption.objects.all(), widget=forms.CheckboxSelectMultiple, required=False)
    allergies = forms.CharField(max_length=128, required=False)

    payment_method = forms.ChoiceField(required=False, choices=(),initial='')
    is_active = forms.BooleanField(required=False, initial=True)
    override_charge = forms.BooleanField(required=False, initial=False)

    class Meta:
        # model = UserProfile
        fields = ('first_name', 'last_name', 'phone', 'mobile_phone', 'date_of_birth', 'weight', 'origin_airport','food_options','allergies', 'email','groups')

    def __init__(self, account, member, *args, **kwargs):
        super(UserProfileForm, self).__init__(*args, **kwargs)

        if account.is_corporate():
            # 13 = Corporate Account Admin
            # 14 = Coordinator
            # 15 = Account Member
            member_group_names = []
            group_names = ['Corporate Account Admin', 'Coordinator', 'Account Member']
            if settings.RISE_ANYWHERE_REQUEST_GROUPS.__len__() > 0:
                group_names.append('Anywhere Flight Creator')
            #RISE 558 only show companion option for new users or for existing companions -- can't "downgrade".
            if member is None or member.user is None or member.user.groups is None:
                group_names.append('Companion')
            if member is not None and member.user is not None and member.user.groups is not None:
                for membergroup in member.user.groups.all():
                    member_group_names.append(membergroup.name)
                if member.user.groups.filter(name = 'Companion').exists():
                    group_names.append('Companion')
                initial = Group.objects.filter(name__in=member_group_names)
            else:
                initial = None
            groups = Group.objects.filter(name__in=group_names)

        else:

            # 12 = Individual Account Admin
            group_names = []
            # if this is an edit and they already have groups, only preselect the groups they are in.
            # Also only add companion as an option if they are already a companion or it is new user.
            if member is None or member.user is None or member.user.groups is None:
                group_names.append('Companion')
            if member is not None and member.user is not None and member.user.groups is not None:
                group_names.append('Individual Account Admin')
                member_group_names = []
                if settings.RISE_ANYWHERE_REQUEST_GROUPS.__len__() > 0:
                    group_names.append('Anywhere Flight Creator')
                for membergroup in member.user.groups.all():
                    member_group_names.append(membergroup.name)
                if member.user.groups.filter(name = 'Companion').exists():
                    group_names.append('Companion')
                initial = Group.objects.filter(name__in=member_group_names)
                groups = Group.objects.filter(name__in=group_names)
            else: #not an edit, they are a companion unless somehow there is no primary user.
                if account.primary_user is None:
                    group_names.append('Individual Account Admin')
                else:
                    group_names.append('Companion')

                groups = Group.objects.filter(name__in=group_names)
                initial = groups

        if member is not None and member.user is not None and member.user.is_staff:
            # add special groups for existing staff member
            staff_groups = Group.objects.filter(name__in=['Pilot', 'Co-Pilot', 'Concierge', 'Operations', 'Admin', 'Monarch', 'Account Member'])
            groups = groups | staff_groups

        self.fields['groups'].queryset = groups
        self.fields['groups'].initial = initial

        pms = account.get_all_payment_methods()
        payment_choices = []
        for pm in pms:
           if pm['nickname'] is not None:
               txt = pm['text'] + " (" + pm['nickname'] + ")"
           else:
               txt = pm['text']
           payment_choices.append( (pm['id'], txt))

        self.fields['payment_method'].choices = payment_choices

        if member is None or member.id is None:
            self.fields['is_active'].initial=True

    def clean_groups(self):
        mygroups = self.cleaned_data.get('groups')
        #ids = ''
        ids = []
        if mygroups:
            for group in mygroups:
                # if ids.__len__() > 0:
                #     ids += ','
                # ids += str(group.id)
                ids.append(group.id)
        if ids.__len__() > 0:
            list = Group.objects.filter(id__in=ids).all()
        else:
            list = {}

        return list

    def clean_payment_methods(self):
        groups = self.cleaned_data.get('groups')
        payment_method = self.cleaned_data.get('payment_method')
        notcoord = groups.exclude(name__in=['Coordinator','Companion']).first()
        if notcoord and not payment_method:
            self._errors['payment_method'] = self.error_class(['You must select a payment method.'])

        return payment_method


    def save(self, account_pk, profile=None):

        if profile is None:
            profile = UserProfile()
            is_new = True
        else:
            is_new = False
        profile.account_id  = account_pk
        profile.first_name = self.cleaned_data.get("first_name")
        profile.last_name = self.cleaned_data.get("last_name")
        profile.email = self.cleaned_data.get("email")
        profile.phone = self.cleaned_data.get("phone")
        profile.mobile_phone = self.cleaned_data.get("mobile_phone")
        profile.date_of_birth = self.cleaned_data.get("date_of_birth")
        profile.weight = self.cleaned_data.get("weight")
        profile.allergies = self.cleaned_data.get("allergies")
        #profile.food_options = self.cleaned_data.get("food_options")
        profile.origin_airport = self.cleaned_data.get("origin_airport")
        profile.save()

        if profile.shipping_address is None:
            profile.shipping_address = Address()
        profile.shipping_address.street_1 = self.cleaned_data.get("ship_street_1")
        profile.shipping_address.street_2 = self.cleaned_data.get("ship_street_2")
        profile.shipping_address.city = self.cleaned_data.get("ship_city")
        profile.shipping_address.state= self.cleaned_data.get("ship_state")
        profile.shipping_address.postal_code = self.cleaned_data.get("ship_postal_code")
        profile.shipping_address.save()
        profile.shipping_address_id = profile.shipping_address.id

        try:
             user = profile.user
        except:
             user = User(userprofile=profile)

        is_active = self.cleaned_data.get("is_active")

        profile.user = user
        profile.user.first_name = profile.first_name
        profile.user.last_name = profile.last_name
        profile.user.email = profile.email
        profile.user.account_id = account_pk
        profile.user.account = profile.account
        profile.user.is_active = is_active
        profile.user.save()

        profile.user.groups = self.cleaned_data.get("groups")
        # If no group is specified, the user is a companion if they are new.  Otherwise they just have no perms
        # we don't want to make existing users into companions if they were previously members because we'll lose track of
        # onboarding.

        if not profile.user.groups.all() and is_new:
            g = Group.objects.get(name='Companion')
            g.user_set.add(profile.user)

        # profile.user.is_active = True
        profile.user.save()

        profile.save()
        return profile

class UserForm(forms.ModelForm):
    """
    A form for creating an account user in the admin
    """

    groups = forms.ModelMultipleChoiceField(queryset=Group.objects.none(), widget=forms.CheckboxSelectMultiple, required=False)

    phone = USPhoneNumberField(required=False)
    mobile_phone = USPhoneNumberField(required=False, error_messages={})

    ship_street_1 = forms.CharField(max_length=128, required=False)
    ship_street_2 = forms.CharField(max_length=128, required=False)
    ship_city = forms.CharField(max_length=64, required=False)
    ship_state = forms.ChoiceField(required=False, choices=STATE_CHOICES, initial='TX')
    ship_postal_code = USZipCodeField(required=False)

    date_of_birth = forms.DateField(widget=forms.DateInput(format='%m/%d/%Y'), input_formats=('%m/%d/%Y', '%m/%d/%y',), required=False)
    weight = forms.ChoiceField(widget=forms.Select, choices=UserProfile.WEIGHT_RANGE_CHOICES)

    origin_airport = AdvancedModelChoiceField(queryset=Airport.objects.all(), widget=forms.RadioSelect, required=False, empty_label=None)

    food_options = forms.ModelMultipleChoiceField(queryset=FoodOption.objects.all(), widget=forms.CheckboxSelectMultiple, required=False)
    allergies = forms.CharField(max_length=128, required=False)

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'groups')

    def __init__(self, account, member, *args, **kwargs):
        super(UserForm, self).__init__(*args, **kwargs)

        if account.is_corporate():
            # 13 = Corporate Account Admin
            # 14 = Coordinator
            # 15 = Account Member
            group_names = ['Corporate Account Admin', 'Coordinator', 'Account Member']
            if settings.RISE_ANYWHERE_REQUEST_GROUPS.__len__() > 0:
                group_names.append('Anywhere Flight Creator')
            if member is not None and member.groups is not None:
                if member.groups.filter(name = 'Companion').exists():
                    group_names.append('Companion')
            groups = Group.objects.filter(name__in=group_names)
            initial = None
        else:

            # 12 = Individual Account Admin
            group_names = ['Individual Account Admin']
            if settings.RISE_ANYWHERE_REQUEST_GROUPS.__len__() > 0:
                group_names.append('Anywhere Flight Creator')
            if member is not None and member.groups is not None:
                if member.groups.filter(name = 'Companion').exists():
                    group_names.append('Companion')
            groups = Group.objects.filter(name__in=group_names)
            initial = groups

        if member is not None and member.is_staff:
            # add special groups for existing staff member
            staff_groups = Group.objects.filter(name__in=['Pilot', 'Co-Pilot', 'Concierge', 'Operations', 'Admin', 'Monarch', 'Account Member'])
            groups = groups | staff_groups

        self.fields['groups'].queryset = groups
        self.fields['groups'].initial = initial


class StaffUserForm(forms.ModelForm):
    """
    A form for creating an account user in the admin
    """

    groups = forms.ModelMultipleChoiceField(queryset=Group.objects.none(), widget=forms.CheckboxSelectMultiple, required=False)

    phone = USPhoneNumberField(required=False)
    mobile_phone = USPhoneNumberField(required=False, error_messages={})

    ship_street_1 = forms.CharField(max_length=128, required=False)
    ship_street_2 = forms.CharField(max_length=128, required=False)
    ship_city = forms.CharField(max_length=64, required=False)
    ship_state = forms.ChoiceField(required=False, choices=STATE_CHOICES, initial='TX')
    ship_postal_code = USZipCodeField(required=False)

    date_of_birth = forms.DateField(widget=forms.DateInput(format='%m/%d/%Y'), input_formats=('%m/%d/%Y', '%m/%d/%y',), required=False)
    weight = forms.ChoiceField(widget=forms.Select, choices=UserProfile.WEIGHT_RANGE_CHOICES)

    origin_airport = AdvancedModelChoiceField(queryset=Airport.objects.all(), widget=forms.RadioSelect, required=False, empty_label=None)

    food_options = forms.ModelMultipleChoiceField(queryset=FoodOption.objects.all(), widget=forms.CheckboxSelectMultiple, required=False)
    allergies = forms.CharField(max_length=128, required=False)

    account = forms.ModelChoiceField(queryset=Account.objects.filter(account_type=Account.TYPE_CORPORATE), widget=forms.Select, required=False, empty_label='--------')

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'groups', 'account')

    def __init__(self, *args, **kwargs):
        super(StaffUserForm, self).__init__(*args, **kwargs)

        # 16 = Pilot
        # 17 = Co-Pilot
        # 18 = Concierge
        # 19 = Operations
        #  1 = Admin
        groups = Group.objects.filter(name__in=['Pilot', 'Co-Pilot', 'Concierge', 'Operations', 'Admin', 'Monarch', 'Account Member'])
        initial = None

        self.fields['groups'].queryset = groups
        self.fields['groups'].initial = initial


class UserNoteForm(forms.ModelForm):
    """
    A form for creating a note about a user in the admin
    """

    class Meta:
        model = UserNote
        fields = ('userprofile', 'created_by', 'body')

    def __init__(self, account, *args, **kwargs):
        member = kwargs.pop('member')
        super(UserNoteForm, self).__init__(*args, **kwargs)
        self.initial['userprofile'] = member



class CreditCardForm(forms.Form):
    """
    A simple payment form for collecting the payment token
    """

    payment_method_nonce = forms.CharField()
    nickname = forms.CharField(max_length=20,required=False,widget=forms.TextInput(attrs={'placeholder': 'Nickname'}))
    is_default = forms.BooleanField(label="Make this payment default", required=False,
        widget=forms.CheckboxInput())


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

    verify_1 = forms.DecimalField(min_value=0.00, max_value=1, max_digits=3, decimal_places=2)
    verify_2 = forms.DecimalField(min_value=0.00, max_value=1, max_digits=3, decimal_places=2)


class ManualChargeForm(forms.ModelForm):
    """
    A form to create a manual charge for an account
    """

    charge_to = forms.ChoiceField(choices=[])

    def __init__(self, account, *args, **kwargs):
        super(ManualChargeForm, self).__init__(*args, **kwargs)

        choices = [('manual', 'Manual')]

        card = account.get_credit_card()
        if card is not None:
            choices.append(('card', 'Credit Card %s' % (card,)))

        bank = account.get_bank_account()
        if bank is not None and bank.verified:
            choices.append(('bank', 'Bank Account %s %s' % (bank.bank_name, bank.last4)))

        self.fields['charge_to'].choices = choices

    class Meta:
        model = Charge
        fields = ('amount', 'description')


class RefundChargeForm(forms.Form):
    """
    A form to issue a refund for a charge
    """

    amount = forms.DecimalField(min_value=0.01, max_digits=10, decimal_places=2)
    description = forms.CharField(max_length=256)

    def __init__(self, charge, *args, **kwargs):
        super(RefundChargeForm, self).__init__(*args, **kwargs)

        self.fields['amount'].validators.append(validators.MaxValueValidator(charge.refund_amount_remaining()))


class VoidChargeForm(forms.Form):
    """
    A form to issue a refund for a charge
    """

    description = forms.CharField(max_length=256)


class InvitationForm(forms.Form):
    """
    A form to add invites or link to a code
    """

    invites = forms.IntegerField(min_value=0)
    code = forms.CharField(max_length=3, required=False)


class UserPasswordForm(forms.Form):
    """
    A form for updating an account user's password in the admin
    """
    new_password1 = forms.CharField(widget=forms.PasswordInput())
    new_password2 = forms.CharField(widget=forms.PasswordInput())

    def __init__(self, *args, **kwargs):
        super(UserPasswordForm, self).__init__(*args, **kwargs)

        self.fields['new_password1'].widget.attrs.update({'autofocus': ''})
        self.fields['new_password1'].error_messages.update({'required': 'New password is required.'})

        self.fields['new_password2'].error_messages.update({'required': 'Please confirm your new password.'})

    def clean(self):
        cleaned_data = super(UserPasswordForm, self).clean()

        new_password1 = cleaned_data.get('new_password1')
        new_password2 = cleaned_data.get('new_password2')

        if new_password1 != new_password2:
            self._errors['new_password1'] = self.error_class(['Password fields do not match.'])


class UserFilterForm(forms.Form):
    """
    A form for selecting filters for Users
    """
    class FilterChoices:
        ALL = ''
        AC = 'a|b|c'
        DF = 'd|e|f'
        GI = 'g|h|i'
        JL = 'j|k|l'
        MO = 'm|n|o'
        PR = 'p|q|r'
        SU = 's|t|u'
        VX = 'v|w|x'
        YZ = 'y|z'

    FILTER_CHOICES = (
        (FilterChoices.ALL, 'ALL MEMBERS'),
        (FilterChoices.AC, 'A-C'),
        (FilterChoices.DF, 'D-F'),
        (FilterChoices.GI, 'G-I'),
        (FilterChoices.JL, 'J-L'),
        (FilterChoices.MO, 'M-O'),
        (FilterChoices.PR, 'P-R'),
        (FilterChoices.SU, 'S-U'),
        (FilterChoices.VX, 'V-X'),
        (FilterChoices.YZ, 'Y-Z')
    )
    filter_user = forms.ChoiceField(choices=FILTER_CHOICES, required=False)


class CustomUserCreationForm(UserCreationForm):
    """
    A form that creates a user, with no privileges, from the given email and
    password.
    """

    def __init__(self, *args, **kargs):
        super(CustomUserCreationForm, self).__init__(*args, **kargs)
        if 'username' in self.fields:
            del self.fields['username']

    class Meta:
        model = User
        fields = ('email',)


class CustomUserChangeForm(UserChangeForm):
    """A form for updating users. Includes all the fields on
    the user, but replaces the password field with admin's
    password hash display field.
    """

    def __init__(self, *args, **kargs):
        super(CustomUserChangeForm, self).__init__(*args, **kargs)
        if 'username' in self.fields:
            del self.fields['username']

    class Meta:
        model = User
        fields = ('email',)


class OnCallScheduleForm(forms.Form):
        user = forms.ModelChoiceField(queryset=User.objects.filter(is_active=1,is_staff=1), widget=forms.Select, required=True)
        startHour = forms.ChoiceField(required=True, choices=OncallSchedule.HOURS)
        endHour = forms.ChoiceField(required=True, choices=OncallSchedule.HOURS)
        airport = forms.ModelChoiceField(queryset=None)
        start_date = forms.DateTimeField(widget=forms.DateInput(format="%m/%d/%Y", attrs={'placeholder': 'MM / DD / YEAR'}),
         label="Start Date", error_messages={'required': 'Start Date is required.'})
        end_date = forms.DateTimeField(widget=forms.DateInput(format="%m/%d/%Y", attrs={'placeholder': 'MM / DD / YEAR'}),
         label="End Date", error_messages={'required': 'End Date is required.'})

        class Meta:
            fields = ('user','airport', 'startHour', 'endHour','start_date','end_date','flights')

        labels = {
            'startHour': 'Time',
            'endHour': 'Time'
        }

        def __init__(self, *args, **kwargs):
            super(OnCallScheduleForm, self).__init__(*args, **kwargs)
            self.fields['airport'].empty_label = 'Airport'
            origin_list = []
            route_list = Route.objects.all()
            for id in route_list:
                origin_list.append(id.origin_id)
            airports = Airport.objects.filter(id__in=origin_list).all()
            self.fields['airport'].queryset = airports
            self.fields['user'].label_from_instance = lambda obj: "%s" % obj.get_full_name()

