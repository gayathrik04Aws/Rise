from django import template
import datetime
from django.conf import settings
from dateutil.relativedelta import relativedelta

from num2words import num2words

from accounts.models import  Account, BillingPaymentMethod
from billing.models import Plan,PlanContractPrice

register = template.Library()


@register.filter(name='num2words')
def number2word(value):
    """
    Returns the humanized word of the given number value
    """
    try:
        return num2words(value)
    except TypeError:
        return ''

@register.filter(name='anywhere_only')
def user_is_anywhere_only(user):
    """
    Returns whether the user is an anywhere_only (Basic OR Plus) member or not based ontheir account's billing plan

    """
    # anonymous users are closer to anywhere only than anything else
    if user.id is None:
        return True
    if user.account is not None and user.account.plan is not None:
        if user.account.plan.anywhere_only:
            return True
        else:
            return False
    elif user.account and user.account.status == Account.STATUS_ACTIVE:
        return False
    else:
        return True

@register.filter(name='anywhere_basic')
def user_is_anywhere_basic(user):
    """
    Returns whether a user has the anywhere basic plan or has not fully upgraded to Plus.
    Used to determine whether we can show the flight request screen
    Args:
        user:

    Returns:

    """
    if user.account is not None and user.account.plan is not None:
        if user.account.plan.name == "RISE ANYWHERE Limited":
            return True
        # if the user is AnywherePlus but has not yet verified bank account, we treat them as if they were Basic.
        if user.account.plan.name == "RISE ANYWHERE" and user.account.is_ach() and user.account.need_verify_bank_account():
            return True
        return False
    elif user.account and user.account.status == Account.STATUS_ACTIVE:
        return False
    else:
        return True

@register.filter(name='anywhere_plus')
def user_is_anywhere_plus(user):
    """
    Returns whether a user has the anywhere plus plan
    Will still return true if they have upgraded but not verified bank account
    Used to determine whether we should show upgrade call-to-action.
    Args:
        user:

    Returns:

    """
    if user.account is not None and user.account.plan is not None and user.account.plan.name == "RISE ANYWHERE":
        return True
    else:
        return False

@register.filter(name="role_is_chargeable")
def is_role_chargeable(is_staff, rolename):
    """
    Returns whether we will charge onboarding for someone in this role.
    Assumes staff do not pay.
    Args:
        is_staff:
        rolename:

    Returns:

    """
    nonchargeable = ['Coordinator','Companion']
    if is_staff:
        return False
    else:
        for val in nonchargeable:
            if val==rolename:
                return False
    return True


@register.filter("load_avatars")
def load_avatars():
    return settings.LOAD_AVATARS


@register.filter(name="user_on_flight")
def user_booked(user, flight):
    return flight.is_booked_by_user(user.userprofile)


@register.filter(name="active_plan_pricing")
def get_active_plan_pricing(account):
    if not account or (not account.get_subscription() and not account.plan):
        return None
    subscription =  account.get_subscription()
    if not subscription:
        if account.founder and account.activated:
            # special case for canceled/suspended account with founder member in 1st year of membership.
            now = datetime.datetime.now()
            delta = now.date() - account.activated.date()
            if delta.days < 365:
                # RISE 472- need to add created as secondary sort because the cancelled one might have same period end.
                lastsubscription = account.subscription_set.order_by('-period_end', '-created').first()
                if lastsubscription:
                    return lastsubscription.amount
        return account.plan.amount
    if not account.plan:
        return subscription.amount
    plan_amt = account.plan.amount
    if subscription.amount != plan_amt and subscription.amount > 0:
        return subscription.amount
    return plan_amt

@register.filter(name="has_discounted_plan")
def is_subscription_less_than_current_plan_price(account):
    if not account or (not account.get_subscription() and not account.plan):
        return None
    subscription =  account.get_subscription()
    if not subscription and account.activated:
         # special case for canceled/suspended account with founder member in 1st year of membership.
        now = datetime.datetime.now()
        delta = now.date() - account.activated.date()
        if delta.days < 365 and account.founder:
            lastsubscription = account.subscription_set.order_by('-period_end', '-created').first()
            if lastsubscription and account.plan:
                if lastsubscription.amount < account.plan.amount:
                    return True
        return False
    if account.plan and subscription:
        if subscription.amount < account.plan.amount:
            return True
    return False

@register.filter(name="get_subscription")
def get_subscription(account):
    subscription = account.get_subscription()
    if subscription is None:
        # special case for founder w/in 1 yr of activation
        if account.founder and account.activated:
            now = datetime.datetime.now()
            delta = now.date() - account.activated.date()
            if delta.days < 365:
                lastsubscription = account.subscription_set.order_by('-period_end','-created').first()
                if lastsubscription and account.plan:
                    if lastsubscription.amount < account.plan.amount:
                        return lastsubscription.amount
        if account.plan:
            return account.plan.amount
        return 0
    return subscription.amount

@register.filter(is_safe=True)
def oncall_time(starthour,endhour):
    meridiem_endhour = "AM"
    meridiem_starthour = "AM"
    if endhour >= 12:
        meridiem_endhour = "PM"
    if starthour >= 12:
        meridiem_starthour = "PM"
    if starthour == 0:
        starthour = 12
    elif starthour > 12:
        starthour = starthour - 12
    if endhour == 0:
        endhour = 12
    elif endhour > 12:
        endhour=endhour-12
    return str(starthour) + ":00 " + meridiem_starthour + " - " + str(endhour) + ":00 " + meridiem_endhour

@register.filter(name="requires_contract")
def does_plan_require_contract(planname):
    plan = Plan.objects.filter(name=planname).first()
    if plan:
        if plan.requires_contract:
            return True
    return False

@register.filter(name="planid_requires_contract")
def does_planid_require_contract(planid):
    plan = Plan.objects.filter(id=planid).first()
    if plan:
        if plan.requires_contract:
            return True
    return False

@register.filter(name="get_plan_id")
def get_plan_id(planname):
    plan = Plan.objects.filter(name=planname).first()
    if plan:
        return plan.id
    return 0

@register.filter(name="get_next_due_date")
def get_next_pay_date(account):
    subscription = account.get_subscription()
    if not subscription:
        return None
    next_start = subscription.period_start + relativedelta(months=1)
    return next_start

@register.filter(name="is_default_payment_method")
def is_default_payment_method(pm_id):
    pm = BillingPaymentMethod.objects.filter(id=pm_id).first()
    return pm.is_default

