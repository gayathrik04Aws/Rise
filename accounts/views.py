from django.views.generic import FormView, TemplateView, View, RedirectView
from django.shortcuts import redirect
from django.db import transaction
from django.utils import timezone
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.models import Group
from django.core.signing import Signer, BadSignature
from django.core.urlresolvers import reverse_lazy
from django.utils.functional import cached_property
from django.utils.http import urlsafe_base64_decode
from django.http import Http404
from django.core.mail import send_mail
from django.template.loader import render_to_string
from pardot import post_to_pardot
from pardot import PardotException
import datetime
from dateutil.relativedelta import relativedelta
import arrow
import mailchimp
import logging
import braintree
import stripe
from billing import paymentMethodUtil

from .forms import (
    SignUpForm, SignUpPaymentForm, SignUpPaymentAnywhereForm, NotifyForm, LandingForm, CorporateSignUpForm, RegisterAccountForm,
    RegisterPaymentForm, PriceCalculatorForm, MemberWelcomeForm, CorporateSignUpConfirmForm, CorporatePaymentForm,
    NotifyWaitlistForm, ReferralInformationForm, ReferralFormSet, AnywhereBasicSignUpForm,
    RegisterAnywhereBasicAccountForm)
from .tokens import invite_token_generator as token_generator
from .models import Invite, User, UserProfile, Account, Address, City,BillingPaymentMethod
from .tasks import mailchimp_subscribe, mailchimp_unsubscribe
from .mixins import LoginRequiredMixin
from billing.models import Card, BankAccount, Subscription, Plan, InvalidUpgradeException, \
    IncompleteUpgradeException, PlanContractPrice
from flights.models import Airport
from anywhere.models import AnywhereFlightSet, AnywhereFlightRequest


stripe.api_key = settings.STRIPE_API_KEY
logger = logging.getLogger(__name__)


class SignUpView(FormView):
    """
    Initial sign up form view to validate invite code or add to waitlist.
    """

    template_name = 'accounts/signup.html'
    form_class = SignUpForm

    def get_initial(self):
        initial = super(SignUpView, self).get_initial()

        origin_city = None
        city = self.request.GET.get('city')

        if city:
            origin_city = next(iter(City.objects.filter(name=city)), None)

        code = None

        email = self.request.session.get('company_email', '')
        first_name = self.request.session.get('company_first_name', '')
        last_name = self.request.session.get('company_last_name', '')
        phone_number = self.request.session.get('company_phone_number', '')



        initial.update({
            'origin_city': origin_city,
            'code': code,
            'first_name': first_name,
            'last_name': last_name,
            'email': email,
            'phone': phone_number,
        })

        if 'invite_id' in self.request.session:
            invite = next(iter(Invite.objects.filter(id=self.request.session['invite_id'])), None)
            if invite is not None:
                initial.update({
                    'email': invite.email,
                    'phone': invite.phone,
                    'first_name': invite.first_name,
                    'last_name': invite.last_name,
                    'origin_city': invite.origin_city,
                    'code': invite.code,
                })

        return initial

    def form_valid(self, form):
        email = form.cleaned_data.get('email')
        first_name = form.cleaned_data.get('first_name', '').strip()
        last_name = form.cleaned_data.get('last_name', '').strip()
        phone_number = form.cleaned_data.get('phone', '').strip()
        origin_city = form.cleaned_data.get('origin_city')
        write_in_city = form.cleaned_data.get('write_in_city', '')
        code = form.cleaned_data.get('code', '')

        origin_city_name = 'Other'
        if origin_city:
            origin_city_name = origin_city.name

        if not code:
            # create an invite code to eventually send
            invite = Invite.objects.create_digital_invite(None, email, origin_city=origin_city, first_name=first_name, last_name=last_name, phone=phone_number)
        else:
            invite = Invite.validate_code(code)

        if invite is not None:
            invite.first_name = first_name
            invite.last_name = last_name
            invite.phone = phone_number
            invite.email = email
            invite.origin_city = origin_city
            invite.save()

            self.request.session['invite_id'] = invite.id

        if origin_city:
            city = origin_city.name
        else:
            city = write_in_city
        url = settings.PARDOT_WEB_SIGNUP_URL
        form_data = {"email":email,"first_name":first_name,"last_name":last_name,"phone":phone_number,
                     "origin_city": city
                     }
        if write_in_city and not origin_city:
            form_data["is_waitlist"] = 1
            form_data["is_limbo"] = 0
        else:
            form_data["is_waitlist"] = 0
            form_data["is_limbo"] = 1
        try:
            post_to_pardot(form_data,url)
        except PardotException as e:
            #ignore the error messages
            error = e.message
        # Add write-ins to the placeholder list so that we can track them just in case they abandon at this point, before paying
        if origin_city is None and write_in_city:
            return redirect('other_city_thanks')

        return redirect('payment_form')


class SignUpAnywhereBasicView(FormView):
    """
    Initial sign up form view for Rise Anywhere invitees
    """

    template_name = 'accounts/signup_anywhere.html'
    form_class = AnywhereBasicSignUpForm

    def get_initial(self):

        initial = super(SignUpAnywhereBasicView, self).get_initial()

        # Removing origin city from RiseAnywhere signup forms since it's not relevant except for marketing
        # and isn't currently stored if not a default city.
        # However I am leaving it in the data structure for simplicity for adding back later.

        origin_city = None
        # city = self.request.GET.get('city')
        #
        # if city:
        #     origin_city = next(iter(City.objects.filter(name=city)), None)

        email = self.request.session.get('company_email', '')
        first_name = self.request.session.get('company_first_name', '')
        last_name = self.request.session.get('company_last_name', '')
        phone_number = self.request.session.get('company_phone_number', '')

        initial.update({
            'origin_city': origin_city,
            'first_name': first_name,
            'last_name': last_name,
            'email': email,
            'phone': phone_number,
        })

        return initial

    def form_valid(self, form):
        flightset_key = self.kwargs.get("slug")
        flightset = AnywhereFlightSet.objects.filter(public_key=flightset_key).first()
        if not flightset:
            return redirect('anywhere_index')

        email = form.cleaned_data.get('email')
        first_name = form.cleaned_data.get('first_name', '').strip()
        last_name = form.cleaned_data.get('last_name', '').strip()
        phone_number = form.cleaned_data.get('phone', '').strip()
        origin_city = form.cleaned_data.get('origin_city')
        write_in_city = form.cleaned_data.get('write_in_city', '')

        origin_city_name = 'Other'
        if origin_city:
            origin_city_name = origin_city.name

        # AMF - There isn't a concept of invite codes in Rise Anywhere but to avoid disrupting
        # the existing process we will create one
        # since these are needed by the paymentform view
        invite = Invite.objects.create_digital_invite(None, email, origin_city=origin_city, first_name=first_name,
                                                      last_name=last_name, phone=phone_number)

        if invite is not None:
             invite.first_name = first_name
             invite.last_name = last_name
             invite.phone = phone_number
             invite.email = email
             invite.origin_city = origin_city
             invite.code='ANYWHERE' #this code will trigger RiseAnywhere only behaviors such as no initiation fee & automated billing plan selection
             invite.save()

        #AMF-billingplanisalwaysAnywhereBasichere,inregularprocessitgetspickedafteracctcreation
        anywhereplan=Plan.objects.filter(name='RISE ANYWHERE Limited').first()
        with transaction.atomic():

            #AMFmarkonboardingfeepaidtoensurethatbankaccountwon'tgetchargedduringverification.
            account=Account.objects.create(founder=False,origin_city=origin_city,
                                           plan=anywhereplan,pass_count=0,companion_pass_count=0,onboarding_fee_paid=0)

            account.save()


            #createtheuserprofile
            up=UserProfile.objects.create(email=email,first_name=first_name, last_name=last_name,phone=phone_number, account=account)
            account.primary_profile = up

            #createtheuserobject
            user=User.objects.create_user(email,first_name,last_name,password=None,account=account, userprofile=up)

            account.primary_user=user

            account.save()

            #commonwelcomeemailforbothACH&CCsincenochargemade.
            account.send_welcome_anywhere_email()

            group=Group.objects.get(name='Individual Account Admin')

            if group is not None:
                user.groups.add(group)

            account.save()


        #ifitisnotagenericinvite,markitasredeemed

        if invite.id>0:
            Invite.objects.filter(id=invite.id).update(redeemed=True,redeemed_on=timezone.now(),redeemed_by=user)


        self.request.session['account_id']=account.id
        invite.account=account
        invite.save()


        url = settings.PARDOT_ANYWHERE_WEB_SIGNUP_URL
        form_data = {"email":email,"first_name":first_name,"last_name":last_name,"phone":phone_number
                     }
        try:
            post_to_pardot(form_data,url)
        except PardotException as e:
            #ignore the error messages
            error = e.message

        #differentversionofadminemailforRiseAnywheretoletadminsknowwealreadysentonboarding,thisisinfopurposesonly.
        account.send_admin_anywhere_signup_email()

        flightset_public_key=self.kwargs.get('slug')
        flightset=AnywhereFlightSet.objects.filter(public_key=flightset_public_key).first()
        flight_creator=flightset.anywhere_request.created_by
        account.primary_user.send_anywhere_onboarding_email(flightset,flight_creator)

        #logtheuserinsotheycanbook
        user.backend='django.contrib.auth.backends.ModelBackend'
        login(self.request,account.primary_user)
        return redirect(reverse_lazy('anywhere_flight_info', kwargs={'slug':flightset_key}))


class CorporateSignUpView(FormView):
    """
    Corporate sign up form view to allow access to the pricing calculator.
    """

    template_name = 'accounts/corporate_signup.html'
    form_class = CorporateSignUpForm

    def get_initial(self):
        initial = super(CorporateSignUpView, self).get_initial()

        if 'invite_id' in self.request.session:
            invite = next(iter(Invite.objects.filter(id=self.request.session['invite_id'])), None)
            if invite is not None:
                initial.update({
                    'email': invite.email,
                    'phone': invite.phone,
                    'first_name': invite.first_name,
                    'last_name': invite.last_name,
                })

        return initial

    def form_valid(self, form):
        email = form.cleaned_data.get('email')
        first_name = form.cleaned_data.get('first_name', '').strip()
        last_name = form.cleaned_data.get('last_name', '').strip()
        company = form.cleaned_data.get('company', '').strip()
        phone_number = form.cleaned_data.get('phone', '').strip()

        if email and first_name and last_name and company and phone_number:

            subject = "Initial Lead from %s at %s regarding Company Membership" % (first_name, company)

            context = {
                'company': company,
                'subject': subject,
                'email': email,
                'first_name': first_name,
                'last_name': last_name,
                'phone_number': phone_number,
            }

            text_content = render_to_string('emails/corporate_signup.txt', context)

            send_mail(subject, text_content, email, ['Rise <info@iflyrise.com>'])

        # adding form data to session for use on the Sign Up Form view
        self.request.session['company'] = company
        self.request.session['company_email'] = email
        self.request.session['company_first_name'] = first_name
        self.request.session['company_last_name'] = last_name
        self.request.session['company_phone_number'] = phone_number

        return redirect('price_calculator')


class CorporateSignUpConfirmView(FormView):
    """
    Corporate sign up form view to allow access to the pricing calculator.
    """

    template_name = 'accounts/corporate_signup_confirm.html'
    form_class = CorporateSignUpConfirmForm

    def get_initial(self):
        initial = super(CorporateSignUpConfirmView, self).get_initial()

        initial.update({
            'company': self.request.session.get('company'),
            'email': self.request.session.get('company_email'),
            'first_name': self.request.session.get('company_first_name'),
            'last_name': self.request.session.get('company_last_name'),
            'phone': self.request.session.get('company_phone_number'),
            'member_count': self.request.session.get('company_member_count'),
            'pass_count': self.request.session.get('company_pass_count'),
        })

        return initial

    def form_valid(self, form):
        data = form.cleaned_data

        account = Account.objects.create(
            company_name=data.get('company'),
            account_type=Account.TYPE_CORPORATE,
            member_count=data.get('member_count'),
            pass_count=data.get('pass_count'),
            companion_pass_count=0,
            plan_id = 2,
        )
         # create the user profile
        up = UserProfile.objects.create(email=data.get('email'), first_name=data.get('first_name'), last_name=data.get('last_name'), phone=data.get('phone'), account=account)


        # create the user object
        user = User.objects.create_user(data.get('email'), data.get('first_name'), data.get('last_name'), password=None, account=account, userprofile=up)

        account.primary_user = user
        account.primary_profile = up
        account.corporate_amount = account.calculate_monthly_corporate_price()
        account.save()

        group = Group.objects.get(name='Corporate Account Admin')

        if group is not None:
            user.groups.add(group)


        self.request.session['company_account_id'] = account.id

        return redirect('corporate_payment_form')


class CorporatePaymentView(FormView):

    form_class = CorporatePaymentForm
    template_name = 'accounts/corporate_signup_payment.html'

    def get_context_data(self, **kwargs):
        context = super(CorporatePaymentView, self).get_context_data(**kwargs)

        client_token = braintree.ClientToken.generate()

        account_id = self.request.session.get('company_account_id')
        account = next(iter(Account.objects.filter(id=account_id)), None)

        context.update({
            'STRIPE_PUBLISHABLE_KEY': settings.STRIPE_PUBLISHABLE_KEY,
            'client_token': client_token,
            'account': account,
            'account_holder_name': account.company_name,
            'account_holder_type':'company',
        })

        return context

    def form_valid(self, form):
        data = form.cleaned_data

        account_id = self.request.session.get('company_account_id')
        account = next(iter(Account.objects.filter(id=account_id)), None)

        if account is None:
            return redirect('corporate_invite_form')

        # create all the user account models in a single transaction
        with transaction.atomic():
            email = self.request.session.get('company_email')
            token = data.get('token')
            nickname = data.get('nickname')
            payment_method = data.get('payment_method')

            if payment_method == 'Card':
                try:
                    # RISE-464 need to pass the actual account instance because we are within a transaction
                    # otherwise when we save the account below we will overwrite the save that occurs inside the
                    # createCreditCard method with our version of the object here.
                    card = paymentMethodUtil.createCreditCard(token, True, account_id, nickname=nickname, account=account)
                    charge = card.charge(account.get_onboarding_fee_total(), 'Initiation Fee',account.primary_user)
                    charge.send_welcome_receipt_email()
                    account.onboarding_fee_paid = True
                    account.payment_method = Account.PAYMENT_CREDIT_CARD
                    account.save()
                except paymentMethodUtil.CardException as e:
                    for error in e.message:
                        form.add_error(None,error)
                    return self.form_invalid(form)

            elif payment_method == 'ACH':
                # RISE-464 need to pass the actual account instance because we are within a transaction
                # otherwise when we save the account below we will overwrite the save that occurs inside the
                # createBankAccount method with our version of the object here.
                paymentMethodUtil.createBankAccount(account_id, token, nickname=nickname, account=account)
                account.payment_method = Account.PAYMENT_ACH
                if account.is_trial():
                    account.status = Account.STATUS_ACTIVE
                account.save()
            elif payment_method == 'Manual':
                account.payment_method = Account.PAYMENT_MANUAL
                if account.is_trial():
                    account.status = Account.STATUS_ACTIVE
                account.save()

        account.send_admin_signup_email()

        return redirect('corporate_thanks')


class CorporateThanksView(TemplateView):
    """
    Simple payment thank you page
    """

    template_name = 'accounts/corporate_signup_thanks.html'

    def get_context_data(self, **kwargs):
        context = super(CorporateThanksView, self).get_context_data(**kwargs)

        account_id = self.request.session.get('company_account_id')
        account = None
        if account_id:
            account = next(iter(Account.objects.filter(pk=account_id)), None)

        context.update({
            'account': account
        })
        return context


class PriceCalculatorView(FormView):
    """
    View the Price Calculator
    """

    template_name = 'accounts/price_calculator.html'
    form_class = PriceCalculatorForm

    def form_valid(self, form):
        num_members = form.cleaned_data.get('num_members', '').strip()
        num_seats = form.cleaned_data.get('num_seats', '').strip()

        company = self.request.session.get('company', '')
        email = self.request.session.get('company_email', '')
        first_name = self.request.session.get('company_first_name', '')
        last_name = self.request.session.get('company_last_name', '')
        phone_number = self.request.session.get('company_phone_number', '')

        self.request.session['company_pass_count'] = num_seats
        self.request.session['company_member_count'] = num_members

        if num_members and num_seats and company and first_name and last_name and email:

            subject = "Inquiry from %s at %s regarding Price Calculator" % (first_name, company)

            context = {
                'company': company,
                'subject': subject,
                'email': email,
                'first_name': first_name,
                'last_name': last_name,
                'phone_number': phone_number,
                'num_members': num_members,
                'num_seats': num_seats
            }

            text_content = render_to_string('emails/price_calculator_inquiry.txt', context)

            send_mail(subject, text_content, email, ['Rise <info@iflyrise.com>'])

        return redirect('corporate_signup_form')


class InviteCodeView(View):
    """
    A view to validate an invite code and redirect to the payment form
    """

    def get(self, request, *args, **kwargs):
        code = kwargs.get('code')
        invite = Invite.validate_code(code)

        if invite is not None:
            self.request.session['invite_id'] = invite.id

            if invite.origin_city is not None:
                return redirect('payment_form')

            messages.error(self.request, 'Please choose an origin city.')

        return redirect('invite_form')


class InviteThanksView(TemplateView):
    """
    Simple thank you view for signing up.
    """

    template_name = 'accounts/signup_thanks.html'


class PaymentFormView(FormView):

    form_class = SignUpPaymentForm
    template_name = 'accounts/payment.html'

    def dispatch(self, request, *args, **kwargs):
        """
        Ensure a valid invite code has been entered and is in the session including an origin city
        """

        invite = self.invite

        if invite is None:
            return redirect('invite_form')

        if invite.origin_city is None:
            messages.error(request, 'Please choose an origin city.')
            return redirect('invite_form')

        return super(PaymentFormView, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(PaymentFormView, self).get_context_data(**kwargs)

        invite = self.invite

        client_token = None
        try:
            client_token = braintree.ClientToken.generate()
        except Exception, e:
            logger.exception(e)

        context.update({
            'STRIPE_PUBLISHABLE_KEY': settings.STRIPE_PUBLISHABLE_KEY,
            'client_token': client_token,
            'invite': invite,
            'city': invite.origin_city,
            'account_holder_name': invite.first_name + ' ' + invite.last_name,
            'account_holder_type':'individual',
        })

        return context

    @cached_property
    def invite(self):
        """
        Returns the invite or None from the invite id stored in the session
        """
        if 'invite_id' in self.request.session:
            return next(iter(Invite.objects.filter(id=self.request.session.get('invite_id'))), None)
        return None

    def get_initial(self):
        initial = super(PaymentFormView, self).get_initial()

        invite = self.invite
        if invite is not None:
            initial.update({
                'email': invite.email,
                'first_name': invite.first_name,
                'last_name': invite.last_name,
                'phone': invite.phone,
                'preferred_cities': [invite.origin_city],
            })

        return initial

    def form_valid(self, form):
        data = form.cleaned_data

        # create all the user account models in a single transaction
        with transaction.atomic():

            first_name = data.get('first_name')
            last_name = data.get('last_name')
            email = data.get('email')
            nickname = data.get('nickname')
            token = data.get('token')

            payment_method = data.get('payment_method')
            stripe_customer_id = None
            braintree_customer_id = None

            if payment_method == 'Card':
                # create the braintree customer with the given payment method token
                result = braintree.Customer.create({
                    'payment_method_nonce': token,
                    'first_name': first_name,
                    'last_name': last_name
                })

                if result.is_success:
                    braintree_customer = result.customer
                    braintree_customer_id = braintree_customer.id
                    braintree_card = braintree_customer.credit_cards[0]

                else:
                    for error in result.errors.deep_errors:
                        form.add_error(None, error.message)
                        return self.form_invalid(form)
            elif payment_method == 'ACH':
                stripe_customer = stripe.Customer.create(description=email, email=email)
                stripe_customer_id = stripe_customer.id
                name = first_name + ' ' + last_name
                # update our local copy of the bank account
                stripe_bank_account = stripe_customer.bank_accounts.create(bank_account=token)

            # create the account
            city = self.invite.origin_city

            account = Account.objects.create(founder=city.is_founder(), origin_city=city, braintree_customer_id=braintree_customer_id, stripe_customer_id=stripe_customer_id)
            charge = None
            bank_account = None

            account.save()

            # RISE-499 have to create the user object before charging in order to store who charged it.
            # create the user object

            # get the billing and shipping addresses
            billing_address = Address.objects.create(street_1=data.get('bill_street_1'),
                                                    street_2=data.get('bill_street_2'),
                                                    city=data.get('bill_city'),
                                                    state=data.get('bill_state'),
                                                    postal_code=data.get('bill_postal_code'))

            if data.get('shipping_same'):
                shipping_address = billing_address
            else:
                shipping_address = Address.objects.create(street_1=data.get('ship_street_1'),
                                                        street_2=data.get('ship_street_2'),
                                                        city=data.get('ship_city'),
                                                        state=data.get('ship_state'),
                                                        postal_code=data.get('ship_postal_code'))
             # create the user profile
            profile = UserProfile.objects.create(account=account, first_name=first_name, last_name=last_name, email=email,  phone=data.get('phone'), billing_address=billing_address, shipping_address=shipping_address)

            # create the user object
            user = User.objects.create_user(email, first_name, last_name, password=None, account=account)
            profile.user = user
            profile.user_id = user.id
            profile.save()

            account.primary_user = user
            account.primary_profile = profile
            account.save()


            if payment_method == 'Card':
                billing_payment_method = BillingPaymentMethod.objects.create_payment_method(account,BillingPaymentMethod.PAYMENT_CREDIT_CARD,nickname,True)
                card = Card.objects.create_from_braintree_card(account, braintree_card,billing_payment_method)
                try:
                    charge_amount = account.get_onboarding_fee_total()
                    charge = card.charge(charge_amount, 'Initiation Fee',user)
                except Exception, e:
                    logger.exception('Initiation Fee submitted by %s %s (%s) was not successful: %s' % (first_name, last_name, email, e))
                    charge_message = 'We\'re sorry. There was an error during processing of the card, and the payment was unsuccessful.'
                    messages.error(self.request, charge_message)
                    return self.form_invalid(form)

                account.onboarding_fee_paid = True
                account.payment_method = Account.PAYMENT_CREDIT_CARD
                account.save()
            elif payment_method == 'ACH':
                billing_payment_method = BillingPaymentMethod.objects.create_payment_method(account,BillingPaymentMethod.PAYMENT_ACH,nickname,True)
                bank_account = BankAccount(account=account,billing_payment_method=billing_payment_method)
                bank_account.update_from_stripe_bank_account(stripe_bank_account)
                bank_account.save()
                account.payment_method = Account.PAYMENT_ACH
                account.save()

            city.update_member_acceptance()

            preferred_cities = data.get('preferred_cities')
            cities_merge_var = ''
            if preferred_cities:
                account.preferred_cities.add(*preferred_cities)

                cities = [preferred_city.name for preferred_city in preferred_cities]
                cities_merge_var = ','.join(cities)



            if charge is not None:
                charge.send_welcome_receipt_email()
                account.update_braintree_customer()

            elif bank_account is not None:
                bank_account.send_welcome_email()

            if account.is_corporate():
                group = Group.objects.get(name='Corporate Account Admin')
            else:
                group = Group.objects.get(name='Individual Account Admin')

            if group is not None:
                user.groups.add(group)

            user.save()



            # if it is not a generic invite, mark it as redeemed
            invite_id = self.request.session.get('invite_id')
            if invite_id > 0:
                Invite.objects.filter(id=invite_id).update(redeemed=True, redeemed_on=timezone.now(), redeemed_by=user)

            # delete invite data from session
            del self.request.session['invite_id']

            self.request.session['account_id'] = account.id
            self.invite.account = account
            self.invite.save()

            form_data = {"email":email,"first_name":first_name,"last_name":last_name,"phone":data.get('phone'),"origin_city":account.origin_city.name
                     }
            url = settings.PARDOT_WEB_SIGNUP_URL
            try:
                post_to_pardot(form_data,url)
            except PardotException as e:
               error = e.message

        account.send_admin_signup_email()

        return redirect('payment_form_thanks')


class PaymentThanksView(TemplateView):
    """
    Simple payment thank you page
    """

    template_name = 'accounts/payment_thanks.html'

    def get_context_data(self, **kwargs):
        context = super(PaymentThanksView, self).get_context_data(**kwargs)

        account_id = self.request.session.get('account_id')
        account = None
        if account_id:
            account = next(iter(Account.objects.filter(pk=account_id)), None)

        context.update({
            'account': account
        })
        return context


class PaymentAnywhereFormView(FormView):
    """
    Split this view out from PaymentFormView for the RiseAnywhere process.
    Eventually we will refactor out the common functions, parameterize and share them between the views / API views.
    But for now we just want to get it working without impacting existing process.

    """

    form_class = SignUpPaymentAnywhereForm
    template_name = 'accounts/payment_anywhere.html'

    def get_context_data(self, **kwargs):
        context = super(PaymentAnywhereFormView, self).get_context_data(**kwargs)

        #I don't see any reason we need invite here.
        # invite = self.invite

        client_token = None
        try:
            client_token = braintree.ClientToken.generate()
        except Exception, e:
            logger.exception(e)

        user = self.request.user

        if user is not None:
            if user.account is not None:
                if user.account.account_type == 'C':
                    account_holder_type = 'company'
                    account_holder_name = user.account.company_name
                else:
                    account_holder_type = 'individual'
                    account_holder_name = user.first_name + ' ' + user.last_name
            else:
                account_holder_type = 'individual'
                account_holder_name = user.first_name + ' ' + user.last_name

        context.update({
            'STRIPE_PUBLISHABLE_KEY': settings.STRIPE_PUBLISHABLE_KEY,
            'client_token': client_token,
            'account_holder_name':account_holder_name,
            'account_holder_type':account_holder_type,
            #'invite': invite,
            #'city': invite.origin_city,
        })

        return context

    def get_initial(self):
        initial = super(PaymentAnywhereFormView, self).get_initial()

        user = self.request.user
        # profile = UserProfile.objects.filter(user_id=user.id).first()
        profile = user.userprofile

        if user is not None:
            initial.update({
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'phone': profile.phone,
                'preferred_cities': [user.account.origin_city],
            })

        return initial

    def form_valid(self, form):
        data = form.cleaned_data

        userprofile = self.request.user.userprofile
        account = self.request.user.account


        # create all the models in a single transaction
        with transaction.atomic():

            first_name = data.get('first_name')
            last_name = data.get('last_name')
            email = data.get('email')

            token = data.get('token')
            nickname = data.get('nickname')
            payment_method = data.get('payment_method')
            stripe_customer_id = None
            braintree_customer_id = None

            if payment_method == 'Card':
                # create the braintree customer with the given payment method token
                result = braintree.Customer.create({
                    'payment_method_nonce': token,
                    'first_name': first_name,
                    'last_name': last_name
                })

                if result.is_success:
                    braintree_customer = result.customer
                    braintree_customer_id = braintree_customer.id
                    braintree_card = braintree_customer.credit_cards[0]

                else:
                    for error in result.errors.deep_errors:
                        form.add_error(None, error.message)
                        return self.form_invalid(form)
            elif payment_method == 'ACH':
                stripe_customer = stripe.Customer.create(description=email, email=email)
                stripe_customer_id = stripe_customer.id

                # update our local copy of the bank account
                stripe_bank_account = stripe_customer.bank_accounts.create(bank_account=token)

            account.braintree_customer_id = braintree_customer_id
            account.stripe_customer_id = stripe_customer_id
            account.save()


            charge = None
            bank_account = None
            #  Skip making an actual charge - no initiation fee on Anywhere accounts
            #  but still capture payment method to be used for booking

            if payment_method == 'Card':
                billing_payment_method = BillingPaymentMethod.objects.create_payment_method(account,BillingPaymentMethod.PAYMENT_CREDIT_CARD,nickname,True)
                Card.objects.create_from_braintree_card(account, braintree_card,billing_payment_method)
                account.payment_method = Account.PAYMENT_CREDIT_CARD
                account.save()
            elif payment_method == 'ACH':
                 billing_payment_method = BillingPaymentMethod.objects.create_payment_method(account,BillingPaymentMethod.PAYMENT_ACH,nickname,True)
                 bank_account = BankAccount(account=account,billing_payment_method=billing_payment_method)
                 bank_account.update_from_stripe_bank_account(stripe_bank_account)
                 bank_account.save()
                 account.payment_method = Account.PAYMENT_ACH
                 account.save()

            # no update_member_acceptance because there are no limits or founder accounts etc.,
            # that is just for regular memberships

            # city.update_member_acceptance()

            preferred_cities = data.get('preferred_cities')
            cities_merge_var = ''
            if preferred_cities:
                account.preferred_cities.add(*preferred_cities)

                cities = [preferred_city.name for preferred_city in preferred_cities]
                cities_merge_var = ','.join(cities)

            account.save()

            if payment_method == 'Card':
                account.update_braintree_customer()

            # get the billing and shipping addresses
            billing_address = Address.objects.create(street_1=data.get('bill_street_1'),
                                                     street_2=data.get('bill_street_2'),
                                                     city=data.get('bill_city'),
                                                     state=data.get('bill_state'),
                                                     postal_code=data.get('bill_postal_code'))

            if data.get('shipping_same'):
                 shipping_address = billing_address
            else:
                 shipping_address = Address.objects.create(street_1=data.get('ship_street_1'),
                                                         street_2=data.get('ship_street_2'),
                                                         city=data.get('ship_city'),
                                                         state=data.get('ship_state'),
                                                         postal_code=data.get('ship_postal_code'))



            # # update the user profile
            # userprofile = UserProfile.objects.filter(user_id=user.id).first()
            userprofile.billing_address = billing_address
            userprofile.shipping_address = shipping_address
            userprofile.save()

        # send onboarding email automatically, this contains invitation info.

        flightset_public_key=self.kwargs.get('slug')

        # return redirect to booking using the flightid from session
        return redirect(reverse_lazy('book_anywhere', kwargs={'slug':flightset_public_key}))

class PaymentAnywherePlusView(FormView):
    """
    Split this view out from PaymentFormView for the RiseAnywhere process.
    Eventually we will refactor out the common functions, parameterize and share them between the views / API views.
    But for now we just want to get it working without impacting existing process.

    """

    form_class = SignUpPaymentAnywhereForm
    template_name = 'accounts/payment_anywhere_plus.html'

    def get_context_data(self, **kwargs):
        context = super(PaymentAnywherePlusView, self).get_context_data(**kwargs)

        #I don't see any reason we need invite here.
        # invite = self.invite

        client_token = None
        try:
            client_token = braintree.ClientToken.generate()
        except Exception, e:
            logger.exception(e)

        user = self.request.user

        if user is not None:
            if user.account is not None:
                if user.account.account_type == 'C':
                    account_holder_type = 'company'
                    account_holder_name = user.account.company_name
                else:
                    account_holder_type = 'individual'
                    account_holder_name = user.first_name + ' ' + user.last_name
            else:
                account_holder_type = 'individual'
                account_holder_name = user.first_name + ' ' + user.last_name

        context.update({
            'STRIPE_PUBLISHABLE_KEY': settings.STRIPE_PUBLISHABLE_KEY,
            'client_token': client_token,
            'account_holder_type':account_holder_type,
            'account_holder_name':account_holder_name,
        })

        return context

    def get_initial(self):
        initial = super(PaymentAnywherePlusView, self).get_initial()

        user = self.request.user
        profile = UserProfile.objects.filter(user_id=user.id).first()

        if user is not None:
            initial.update({
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'phone': profile.phone,
                'preferred_cities': [user.account.origin_city],
            })

        return initial

    def form_valid(self, form):
        data = form.cleaned_data


        user = self.request.user
        account = self.request.user.account


        # create all the models in a single transaction
        with transaction.atomic():

            first_name = data.get('first_name')
            last_name = data.get('last_name')
            email = data.get('email')

            token = data.get('token')
            nickname = data.get('nickname')
            payment_method = data.get('payment_method')
            stripe_customer_id = None
            braintree_customer_id = None

            if payment_method == 'Card':
                # create the braintree customer with the given payment method token
                result = braintree.Customer.create({
                    'payment_method_nonce': token,
                    'first_name': first_name,
                    'last_name': last_name
                })

                if result.is_success:
                    braintree_customer = result.customer
                    braintree_customer_id = braintree_customer.id
                    braintree_card = braintree_customer.credit_cards[0]

                else:
                    for error in result.errors.deep_errors:
                        form.add_error(None, error.message)
                        return self.form_invalid(form)
            elif payment_method == 'ACH':
                stripe_customer = stripe.Customer.create(description=email, email=email)
                stripe_customer_id = stripe_customer.id

                # update our local copy of the bank account
                stripe_bank_account = stripe_customer.bank_accounts.create(bank_account=token)

            account.braintree_customer_id = braintree_customer_id
            account.stripe_customer_id = stripe_customer_id
            account.save()


            charge = None
            bank_account = None
            #  Skip making an actual charge - no initiation fee on Anywhere accounts
            #  but still capture payment method to be used for booking

            if payment_method == 'Card':
                billing_payment_method = BillingPaymentMethod.objects.create_payment_method(account,BillingPaymentMethod.PAYMENT_CREDIT_CARD,nickname,True)
                Card.objects.create_from_braintree_card(account, braintree_card,billing_payment_method)
                account.payment_method = Account.PAYMENT_CREDIT_CARD
                account.save()
            elif payment_method == 'ACH':
                 billing_payment_method = BillingPaymentMethod.objects.create_payment_method(account,BillingPaymentMethod.PAYMENT_ACH,nickname,True)
                 bank_account = BankAccount(account=account,billing_payment_method=billing_payment_method)
                 bank_account.update_from_stripe_bank_account(stripe_bank_account)
                 bank_account.save()
                 account.payment_method = Account.PAYMENT_ACH
                 account.save()

            # no update_member_acceptance because there are no limits or founder accounts etc.,
            # that is just for regular memberships

            # city.update_member_acceptance()

            preferred_cities = data.get('preferred_cities')
            cities_merge_var = ''
            if preferred_cities:
                account.preferred_cities.add(*preferred_cities)

                cities = [preferred_city.name for preferred_city in preferred_cities]
                cities_merge_var = ','.join(cities)

            account.save()

            if payment_method == 'Card':
                account.update_braintree_customer()

            # get the billing and shipping addresses
            billing_address = Address.objects.create(street_1=data.get('bill_street_1'),
                                                     street_2=data.get('bill_street_2'),
                                                     city=data.get('bill_city'),
                                                     state=data.get('bill_state'),
                                                     postal_code=data.get('bill_postal_code'))

            if data.get('shipping_same'):
                 shipping_address = billing_address
            else:
                 shipping_address = Address.objects.create(street_1=data.get('ship_street_1'),
                                                         street_2=data.get('ship_street_2'),
                                                         city=data.get('ship_city'),
                                                         state=data.get('ship_state'),
                                                         postal_code=data.get('ship_postal_code'))



            # # update the user profile
            userprofile = UserProfile.objects.filter(user_id=user.id).first()
            userprofile.billing_address = billing_address
            userprofile.shipping_address = shipping_address
            userprofile.save()

            # upgrade the plan
            try:
                self.request.user.account.upgrade_anywherebasic_to_plus(user=self.request.user)
                messages.success(self.request, "Congratulations!  You are now an Anywhere Plus member!")
            except InvalidUpgradeException as inv:
                messages.error(self.request, inv.message)
            except IncompleteUpgradeException as inc:
                # this just means they have to verify their bank account so isn't a failure.
                messages.success(self.request, inc.message)
            except ReferenceError as re:
                messages.error(self.request, re.message)

        return redirect(reverse_lazy("anywhere_index"))

class NotifyFormView(FormView):
    """
    A view for someone to put in their email and preferred cities and send it to pardot
    """

    template_name = 'accounts/notify.html'
    form_class = NotifyForm
    success_url = reverse_lazy('notify')

    def form_valid(self, form):
        """
        Send form info to pardot
        """
        first_name = form.cleaned_data.get('first_name')
        last_name = form.cleaned_data.get('last_name')
        email = form.cleaned_data.get('email')
        preferred_cities = form.cleaned_data.get('preferred_cities')

        cities = [city.name for city in preferred_cities]
        cities = ','.join(cities)

        form_data = {"email":email,"first_name":first_name,"last_name":last_name,
                     "city": cities
                     }
        url = settings.PARDOT_NOTIFY_WAIT_LIST
        try:
            post_to_pardot(form_data,url)
        except PardotException as e:
            messages.error(self.request, e.message)
            return self.render_to_response(self.get_context_data())

        messages.info(self.request, 'Thank you for signing up!')

        return super(NotifyFormView, self).form_valid(form)


class NotifyWaitlistFormView(FormView):
    """
    A view for someone to put in their email and preferred cities and send it to pardot
    """

    template_name = 'accounts/notify_waitlist.html'
    form_class = NotifyWaitlistForm
    success_url = settings.WP_URL

    def get_city(self):
        return self.request.GET.get('city', '')

    def get_context_data(self, **kwargs):
        context = super(NotifyWaitlistFormView, self).get_context_data(**kwargs)

        city = self.get_city()
        context.update({
            'city': city
        })

        return context

    def form_valid(self, form):
        """
        Send form info to pardot
        """
        first_name = form.cleaned_data.get('first_name')
        last_name = form.cleaned_data.get('last_name')
        email = form.cleaned_data.get('email')
        city = form.cleaned_data.get('city')

        url = settings.PARDOT_NOTIFY_WAIT_LIST
        form_data = {"email":email,"first_name":first_name,"last_name":last_name,
                     "city": city
                     }
        try:
            post_to_pardot(form_data,url)
        except PardotException as e:
            messages.error(self.request, e.message)
            return self.render_to_response(self.get_context_data())

        messages.info(self.request, 'Thank you for joining the waitlist!')

        return super(NotifyWaitlistFormView, self).form_valid(form)


class LandingFormView(FormView):
    """
    A view for someone to put in their email and preferred cities and send it to pardot
    """

    template_name = 'accounts/events.html'
    form_class = LandingForm
    success_url = reverse_lazy('events')

    def form_valid(self, form):

        first_name = form.cleaned_data.get('first_name')
        last_name = form.cleaned_data.get('last_name')
        email = form.cleaned_data.get('email')

        form_data = {"email":email,"first_name":first_name,"last_name":last_name
                     }
        url = settings.PARDOT_LANDING_LIST
        try:
            post_to_pardot(form_data,url)
        except PardotException as e:
            messages.error(self.request, e.message)
            return self.render_to_response(self.get_context_data())

        messages.info(self.request, 'Thank you for signing up!')

        return super(LandingFormView, self).form_valid(form)


class RegisterLoginView(RedirectView):
    """
    Accepts a signed URL to login a user to begin the registration flow
    """

    pattern_name = 'register_account'

    def get_redirect_url(self, *args, **kwargs):
        """
        If the URL is valid for a given user, log them in and redirect to the regisration account page.

        Else, return None so the redirect view returns a 410 Gone error.
        """
        pk = self.kwargs.get('pk')
        signature = self.kwargs.get('signature')
        value = ':'.join((pk, signature,))
        signer = Signer()

        try:
            pk = signer.unsign(value)
        except BadSignature:
            return None

        user = User.objects.get(id=pk)
        user.backend = 'django.contrib.auth.backends.ModelBackend'
        login(self.request, user)

        #separate register page for Anywhere for now

        if user.account.plan is not None and user.account.plan.anywhere_only:
            self.pattern_name="register_anywhere_account"

        return reverse_lazy(self.pattern_name)


class RegisterAccountView(LoginRequiredMixin, FormView):
    """
    A form view to allow the user to begin setting up their account.
    """

    template_name = 'accounts/register_account.html'
    form_class = RegisterAccountForm
    success_url = reverse_lazy('register_payment')

    def get_initial(self):
        initial = super(RegisterAccountView, self).get_initial()

        user = self.request.user

        try:
            user_profile = user.userprofile
        except:
            user_profile = None

        if user_profile is not None:
            initial.update({'date_of_birth': user.userprofile.date_of_birth})

        initial.update({
            'member_plan': user.account.plan,
            'contract':user.account.contract,
            'pass_count': user.account.pass_count,
            'member_count': user.account.member_count,
            'company_name': user.account.company_name,
        })

        return initial

    def form_valid(self, form):
        # save the form which will set the user's password
        form.save()

        data = form.cleaned_data
        user = self.request.user

        if data.get('contract_signature'):
            user.account.contract_signature = data.get('contract_signature')
        if data.get('contract_signdate'):
            user.account.contract_signeddate = data.get('contract_signdate')


        try:
            user_profile = user.userprofile
        except:
            user_profile = UserProfile(user=user)

        user_profile.date_of_birth = data.get('date_of_birth')
        if user.account.origin_city is not None:
            user.userprofile.origin_airport = user.account.origin_city.airport

        if user.userprofile.origin_airport is None:
            user.userprofile.origin_airport = Airport.objects.get(pk=1)

        user_profile.save()

        if user.account.is_corporate():
            admin_group = Group.objects.get(name='Corporate Account Admin')
            user.account.company_name = data.get('company_name')

            user.account.available_passes = user.account.pass_count
            user.account.available_companion_passes = user.account.companion_pass_count
            user.account.complimentary_passes = 0
            user.account.complimentary_companion_passes = 0
        else:
            admin_group = Group.objects.get(name='Individual Account Admin')
            user.account.plan = data.get('member_plan')
            user.account.contract = data.get('contract')
            user.account.pass_count = user.account.plan.pass_count
            user.account.companion_pass_count = user.account.plan.companion_passes

            user.account.available_passes = user.account.plan.pass_count
            user.account.available_companion_passes = user.account.plan.companion_passes

        if not user.groups.filter(id=admin_group.id).exists():
            user.groups.add(admin_group)

        user.account.activated = arrow.now().datetime
        user.account.save()

        return super(RegisterAccountView, self).form_valid(form)

    def get_form_kwargs(self):
        kwargs = super(RegisterAccountView, self).get_form_kwargs()

        kwargs.update({
            'user': self.request.user,
        })

        return kwargs

class RegisterAnywhereBasicAccountView(LoginRequiredMixin, FormView):
    """
    A form view to allow the user to begin setting up their account.
    """

    template_name = 'accounts/register_anywhere_account.html'
    form_class = RegisterAnywhereBasicAccountForm
    success_url = reverse_lazy('register_payment')

    def get_initial(self):
        initial = super(RegisterAnywhereBasicAccountView, self).get_initial()

        user = self.request.user

        try:
            user_profile = user.userprofile
        except:
            user_profile = None

        if user_profile is not None:
            initial.update({'date_of_birth': user.userprofile.date_of_birth})

        #none of these apply for Anywhere
        # initial.update({
        #     'member_plan': user.account.plan,
        #     'pass_count': user.account.pass_count,
        #     'member_count': user.account.member_count,
        #     'company_name': user.account.company_name,
        # })

        return initial

    def form_valid(self, form):
        # save the form which will set the user's password
        form.save()

        data = form.cleaned_data
        user = self.request.user

        try:
            user_profile = user.userprofile
        except:
            user_profile = UserProfile(user=user)

        user_profile.date_of_birth = data.get('date_of_birth')
        if user.account.origin_city is not None:
            user.userprofile.origin_airport = user.account.origin_city.airport

        if user.user_profile.origin_airport is None:
            user.userprofile.origin_airport = Airport.objects.get(pk=1)

        user_profile.save()

        # if user.account.is_corporate():
        #     admin_group = Group.objects.get(name='Corporate Account Admin')
        #     user.account.company_name = data.get('company_name')
        #
        #     user.account.available_passes = user.account.pass_count
        #     user.account.available_companion_passes = user.account.companion_pass_count
        #     user.account.complimentary_passes = 0
        #     user.account.complimentary_companion_passes = 0
        # else:
        admin_group = Group.objects.get(name='Individual Account Admin')

        # user.account.plan = data.get('member_plan')
        # user.account.pass_count = user.account.plan.pass_count
        # user.account.companion_pass_count = user.account.plan.companion_passes
        #
        # user.account.available_passes = user.account.plan.pass_count
        # user.account.available_companion_passes = user.account.plan.companion_passes

        if not user.groups.filter(id=admin_group.id).exists():
            user.groups.add(admin_group)

        user.account.activated = arrow.now().datetime
        user.account.plan = form.cleaned_data.get('member_plan')

        user.account.save()

        return super(RegisterAnywhereBasicAccountView, self).form_valid(form)

    def get_form_kwargs(self):
        kwargs = super(RegisterAnywhereBasicAccountView, self).get_form_kwargs()

        kwargs.update({
            'user': self.request.user,
        })

        return kwargs

class RegisterPaymentView(LoginRequiredMixin, FormView):
    """
    A form view for collecting a user's payment preference.

    Allows a user to continue using their existing card or bank account if they have one.
    Allows a user to enter a new credit card
    Allows a user to setup a bank account
    Allows a corporate account user to setup a manual payment process.
    """

    template_name = 'accounts/register_payment.html'
    form_class = RegisterPaymentForm
    success_url = reverse_lazy('register_thanks')

    def form_valid(self, form, **kwargs):
        data = form.cleaned_data
        user = self.request.user
        payment_choice = data.get('payment_choice')
        card=None
        if payment_choice == 'existing_card':
            with transaction.atomic():
                user.account.payment_method = Account.PAYMENT_CREDIT_CARD
                user.account.status = Account.STATUS_ACTIVE
                if user.account.contract:
                    user.account.contract_start_date = datetime.datetime.now()
                    user.account.contract_end_date = user.account.contract_start_date + relativedelta(months=user.account.contract.contract_length)

                user.account.save()
            card = user.account.get_credit_card()
        elif payment_choice == 'existing_ach':
            with transaction.atomic():
                user.account.payment_method = Account.PAYMENT_ACH
                # verify they didn't already verify it.  with Anywhere Plus workflow it is possible to do so (though unlikely)
                if user.account.need_verify_bank_account():
                    user.account.status = Account.STATUS_PENDING_ACH
                else:
                    if user.account.contract:
                        user.account.contract_start_date = datetime.datetime.now()
                        user.account.contract_end_date = user.account.contract_start_date + relativedelta(months=user.account.contract.contract_length)
                        user.account.status = Account.STATUS_ACTIVE
                    user.account.save()
            card = user.account.get_bank_account(verified=True)
        elif payment_choice == 'new':
            with transaction.atomic():
                user.account.payment_method = Account.PAYMENT_CREDIT_CARD
                if user.account.contract:
                    user.account.contract_start_date = datetime.datetime.now()
                    user.account.contract_end_date = user.account.contract_start_date + relativedelta(months=user.account.contract.contract_length)

                user.account.status = Account.STATUS_ACTIVE
                user.account.save()

                # get the billing addresses
                billing_address = Address.objects.create(
                    street_1=data.get('bill_street_1'),
                    street_2=data.get('bill_street_2'),
                    city=data.get('bill_city'),
                    state=data.get('bill_state'),
                    postal_code=data.get('bill_postal_code')
                )

                user.userprofile.billing_address = billing_address
                user.userprofile.save()

                payment_method_nonce = data.get('payment_method_nonce')
                nickname=data.get('nickname')
                try:
                    card = paymentMethodUtil.createCreditCard(payment_method_nonce, False, user.account.id, nickname)
                except paymentMethodUtil.CardException as e:
                    for error in e.message:
                        form.add_error(None,error)
                    return self.form_invalid(form)
        elif payment_choice == 'ach':
            with transaction.atomic():
                user.account.payment_method = Account.PAYMENT_ACH

                if user.account.is_trial():
                    user.account.status = Account.STATUS_ACTIVE
                else:
                    user.account.status = Account.STATUS_PENDING_ACH

                user.account.save()

                # get the billing addresses
                billing_address = Address.objects.create(
                    street_1=data.get('bill_street_1'),
                    street_2=data.get('bill_street_2'),
                    city=data.get('bill_city'),
                    state=data.get('bill_state'),
                    postal_code=data.get('bill_postal_code')
                )

                user.userprofile.billing_address = billing_address
                user.userprofile.save()

                stripe_token = data.get('token')
                nickname=data.get('nickname')
                card = paymentMethodUtil.createBankAccount(user.account.id, stripe_token, nickname)

        elif payment_choice == 'manual':
            user.account.payment_method = Account.PAYMENT_MANUAL

            if user.account.is_trial():
                user.account.status = Account.STATUS_ACTIVE
            else:
                # for manual accounts that are not trials, send support an email with the payment info
                name = '%s (%s)' % (user.get_full_name(), user.account.company_name) if user.account.company_name else user.get_full_name()
                subject = 'New Member Payment Info: %s' % name
                from_email = '%s <%s>' % (user.get_full_name(), user.email)
                to_email = 'support@iflyrise.com'
                phone = user.user_profile.phone
                billing = user.user_profile.billing_address
                shipping = user.user_profile.shipping_address
                origin_city = user.account.origin_city

                message_body = "New Member Manual Payment\n**************************\n\nContact Info:\n\nName: %s\nEmail: %s\nPhone: %s\nOrigin City: %s\n\nBilling Address:\n%s\n\nShipping Address:\n%s" % (name, user.email, phone, origin_city, billing, shipping)
                if user.account.is_corporate() and not user.account.onboarding_fee_paid:
                    message_body += "\n\nTeam Members: %d\n\nDeposit owed: $%d ($%d/member) + %d tax (%s)\n" % (user.account.member_count, user.account.get_onboarding_fee(), settings.DEPOSIT_COST, user.account.get_onboarding_fee_tax(), settings.DEPOSIT_TAX_PERCENT)
                send_mail(subject, message_body, from_email, [to_email],)

            user.account.save()

        subscription = user.account.get_subscription()
        charge_card = False
        if card is not None:
            if hasattr(card,'verified'):
                if card.verified:
                    charge_card = True
            else:
                charge_card = True
        if subscription is None:
            if charge_card:
                Subscription.objects.create_subscription(user.account, created_by=user,payment_method_id=card.billing_payment_method_id)
            else:
                Subscription.objects.create_subscription(user.account, created_by=user)

        # only pay onboarding fee now if credit card. ACH will have to wait until verified
        onboarding_fee = user.account.get_onboarding_fee_total()

        if onboarding_fee > 0 and not user.account.onboarding_fee_paid and charge_card:
            if user.account.is_corporate():
                description = "Fee for %d team members ($%d/member) + %s tax)" % (user.account.member_count, settings.DEPOSIT_COST, settings.DEPOSIT_TAX_PERCENT)
            else:
                description = 'Member initation fee'

            if charge_card:
                charge = card.charge(onboarding_fee, description, self.request.user)
                charge.send_receipt_email(subtotal=user.account.get_onboarding_fee(), tax=user.account.get_onboarding_fee_tax(),
                                          tax_percentage=settings.DEPOSIT_TAX_PERCENT)
                user.account.update_braintree_customer()
                user.account.onboarding_fee_paid = True
                user.account.save()

        return super(RegisterPaymentView, self).form_valid(form)

    def get_form_kwargs(self):
        kwargs = super(RegisterPaymentView, self).get_form_kwargs()

        kwargs.update({
            'user': self.request.user,
        })

        return kwargs

    def get_context_data(self, **kwargs):
        context = super(RegisterPaymentView, self).get_context_data(**kwargs)

        account = self.request.user.account

        if account.has_braintree():
            client_token = braintree.ClientToken.generate({'customer_id': account.braintree_customer_id})
        else:
            client_token = braintree.ClientToken.generate()

        card = account.get_credit_card()
        bank_account = account.get_bank_account()
        user = self.request.user
        if user is not None:
            if user.account is not None:
                if user.account.account_type == 'C':
                    account_holder_type = 'company'
                    account_holder_name = user.account.company_name
                else:
                    account_holder_type = 'individual'
                    account_holder_name = user.first_name + ' ' + user.last_name
            else:
                account_holder_type = 'individual'
                account_holder_name = user.first_name + ' ' + user.last_name

        context.update({
            'card': card,
            'bank_account': bank_account,
            'STRIPE_PUBLISHABLE_KEY': settings.STRIPE_PUBLISHABLE_KEY,
            'client_token': client_token,
            'unit_deposit': settings.DEPOSIT_COST,
            'unit_deposit_tax': settings.DEPOSIT_TAX_PERCENT,
            'total_deposit': account.get_onboarding_fee_total(),
            'account_holder_name': account_holder_name,
            'account_holder_type': account_holder_type,
        })

        return context


class RegistrationThanksView(LoginRequiredMixin, TemplateView):

    template_name = 'accounts/registration_thanks.html'


class RegisterMemberFormView(FormView):
    """
    A view to accept new members, set their password, log them in, and redirect them to the edit profile view
    """
    template_name = 'accounts/registration/member_welcome_form.html'
    form_class = MemberWelcomeForm

    @cached_property
    def user(self):
        try:
            uid = urlsafe_base64_decode(self.kwargs.get('uidb64'))
            user = User.objects.get(pk=uid)
            if not token_generator.check_token(user, self.kwargs.get('token')):
                raise Http404
            return user
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            raise Http404

    def get_initial(self):
        initial = super(RegisterMemberFormView, self).get_initial()

        user = self.user

        try:
            user_profile = user.user_profile
        except:
            user_profile = None

        if user_profile is not None:
            initial.update({'date_of_birth': user.user_profile.date_of_birth})

        return initial

    def get_context_data(self, **kwargs):
        context = super(RegisterMemberFormView, self).get_context_data(**kwargs)

        context.update({
            'member': self.user,
        })

        return context

    def get_form_kwargs(self):
        kwargs = super(RegisterMemberFormView, self).get_form_kwargs()

        kwargs.update({
            'user': self.user,
        })

        return kwargs

    def form_valid(self, form):
        user = form.save()

        try:
            user_profile = user.userprofile
        except:
            user_profile = UserProfile(user=user)

        user_profile.date_of_birth = form.cleaned_data.get('date_of_birth')

        try:
            if user.account.origin_city is not None:
                user.userprofile.origin_airport = user.account.origin_city.airport
        except:
            # user doesn't have an account most likely, No worries.
            pass

        if user.userprofile.origin_airport is None:
            user.userprofile.origin_airport = Airport.objects.get(pk=1)

        user_profile.save()

        user.backend = 'django.contrib.auth.backends.ModelBackend'
        login(self.request, user)

        if user.is_staff:
            return redirect('admin_dashboard')
        else:
            return redirect('profile_edit')


class LoggedIn(LoginRequiredMixin, View):
    """
    Intermediate view to check user's groups for possible redirects on logging in.
    """
    def dispatch(self, request, *args, **kwargs):
        # check user's groups for possible redirects
        if self.request.user.groups.filter(name='Concierge').exists():
            return redirect('admin_dashboard')
        elif self.request.user.groups.filter(name='Monarch').exists():
            return redirect('admin_background_check')
        elif self.request.user.groups.filter(name='Pilot').exists():
            return redirect('admin_list_flights')
        else:
            return redirect('dashboard')  # TODO is there a faster way to load the default?


class ReferView(FormView):
    """
    Initial sign up form view to validate invite code or add to waitlist.
    """

    template_name = 'accounts/refer.html'
    form_class = ReferralInformationForm
    success_url = reverse_lazy('refer_thanks')

    def get_referral_formset_kwargs(self):
        kwargs = {
            'prefix': 'referral',
        }

        if self.request.method in ('POST', 'PUT'):
            kwargs.update({
                'data': self.request.POST,
            })
        return kwargs

    def get_referral_formset(self):
        """
        Returns keyword arguments for referrals formset
        """
        kwargs = self.get_referral_formset_kwargs()
        return ReferralFormSet(**kwargs)

    def form_valid(self, form, referral_forms):
        """
        Save the collaboration, save the attachments and then set as the attachments for the collaboration
        and redirect to success_url
        """
        response = super(ReferView, self).form_valid(form)

        name = form.cleaned_data.get('your_name')
        email = form.cleaned_data.get('your_email')
        referrals = []
        form_data = {
            "your_name":name,
            "your_email":email
        }
        print "SUBMITTER: %s - %s" % (name, email)
        url = settings.PARDOT_WEB_REFERRAL_URL
        for index, referral in enumerate(referral_forms):
            # TODO add each referral to the email
            referral_name = referral.cleaned_data.get('name')
            referral_email = referral.cleaned_data.get('email')
            referral_phone = referral.cleaned_data.get('phone')
            print "REFERRAL: %s %s %s" % (referral_name, referral_email, referral_phone)
            referrals.append({
                'name': referral.cleaned_data.get('name'),
                'email': referral.cleaned_data.get('email'),
                'phone': referral.cleaned_data.get('phone')
            })
            form_data["name"] = referral.cleaned_data.get('name')
            form_data["email"] = referral.cleaned_data.get('email')
            form_data["phone"] = referral.cleaned_data.get('phone')
            try:
                post_to_pardot(form_data,url)
            except PardotException as e:
                error = e.message
                messages.error(self.request, error)
                return self.render_to_response(self.get_context_data())

        if email and name and len(referrals) > 0:

            subject = "Referrals from %s" % (name)

            context = {
                'subject': subject,
                'email': email,
                'name': name,
                'referrals': referrals
            }

            text_content = render_to_string('emails/referrals.txt', context)

            send_mail(subject, text_content, email, ['Rise <info@iflyrise.com>'])

        return response

    def form_invalid(self, form, referral_forms):
        """
        If the form is invalid, re-render the context data with the
        data-filled form and errors.
        """
        return self.render_to_response(self.get_context_data(form=form,
                                                             referral_forms=referral_forms))

    def get(self, request, *args, **kwargs):
        self.object = None
        form = self.get_form()
        referral_forms = self.get_referral_formset()
        return self.render_to_response(self.get_context_data(form=form,
                                                             referral_forms=referral_forms))

    def post(self, request, *args, **kwargs):
        self.object = None
        form = self.get_form()
        referral_forms = self.get_referral_formset()
        form_valid = form.is_valid()
        referral_forms_valid = referral_forms.is_valid()
        if form_valid and referral_forms_valid:
            return self.form_valid(form, referral_forms)
        else:
            return self.form_invalid(form, referral_forms)


class ReferThanksView(TemplateView):
    """
    Thank you view following a referral submission
    """
    template_name = 'accounts/refer_thanks.html'
