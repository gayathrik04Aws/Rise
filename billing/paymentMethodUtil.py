from .models import Card,BankAccount
from accounts.models import BillingPaymentMethod,Account
import braintree
import stripe

class CardException(Exception):
   pass

def deleteCreditCard(card_id):
    card = Card.objects.filter(id=card_id).first()
    if card is not None:
        billing_payment_method = BillingPaymentMethod.objects.filter(id=card.billing_payment_method_id).first()
        card.delete()
        billing_payment_method.delete()

def deleteBankAccountView(bank_id,account_id):
    bankaccount = BankAccount.objects.filter(id=bank_id).first()
    account = Account.objects.filter(id=account_id).first()
    if bankaccount is not None:
        billing_payment_method = BillingPaymentMethod.objects.filter(id=bankaccount.billing_payment_method_id).first()
        bankaccount.delete()
        billing_payment_method.delete()
        if BankAccount.objects.filter(account=account).count() <= 0:
            account.stripe_customer_id=None
            account.save()

def setDefaultPayment(billing_payment_method_id,account_id):
    billing_payment_method = BillingPaymentMethod.objects.filter(account_id=account_id,is_default=True).first()
    if billing_payment_method is not None:
        billing_payment_method.is_default=False
        billing_payment_method.save()

    billing_payment_method = BillingPaymentMethod.objects.filter(id=billing_payment_method_id).first()
    billing_payment_method.is_default=True
    billing_payment_method.save()


def createCreditCard(payment_method_nonce,is_default,account_id,nickname=None,account=None):
    # RISE-464 this operation might be within an outside transaction scope in which case
    # we need to operate on that same instance of the account object.  Only load a new instance
    # if we don't get one passed in.
    if account is None:
        account=Account.objects.filter(id=account_id).first()
    if is_default:
        BillingPaymentMethod.objects.filter(account_id=account_id,is_default=True).update(is_default=False)
    if account.has_braintree():
        result = braintree.PaymentMethod.create({
            'customer_id': account.braintree_customer_id,
            'payment_method_nonce': payment_method_nonce,
            'options': {
                'make_default': True
            }
        })

        if result.is_success:
            billing_payment_method = BillingPaymentMethod.objects.create_payment_method(account,BillingPaymentMethod.PAYMENT_CREDIT_CARD,nickname,is_default)
            card = Card.objects.create_from_braintree_card(account, result.payment_method,billing_payment_method)
            account.update_braintree_customer()
            return card
        else:
            errors = []
            for error in result.errors.deep_errors:
                errors.append(error.message)
            raise CardException(errors)
    else:
        member = account.primary_user
        first_name = ''
        last_name = ''
        email = ''
        if member:
            first_name = member.first_name
            last_name = member.last_name
            email = member.email

        # create the braintree customer with the given payment method token
        result = braintree.Customer.create({
            'payment_method_nonce': payment_method_nonce,
            'first_name': first_name,
            'last_name': last_name,
            'company': account.company_name,
            'email': email
        })

        if result.is_success:
            braintree_customer = result.customer
            account.braintree_customer_id = braintree_customer.id
            account.save(update_fields=['braintree_customer_id'])

            braintree_card = braintree_customer.credit_cards[0]
            #Card.objects.filter(account=self.account).delete()  # delete any stripe cards
            billing_payment_method = BillingPaymentMethod.objects.create_payment_method(account,BillingPaymentMethod.PAYMENT_CREDIT_CARD,nickname,is_default)
            card = Card.objects.create_from_braintree_card(account, braintree_card,billing_payment_method)
            return card
        else:
            errors = []
            for error in result.errors.deep_errors:
                errors.append(error.message)
            raise CardException(errors)


def createBankAccount(account_id,token,nickname=None,routing=None,last4=None, account=None):
    # RISE-464 this operation might be within an outside transaction scope in which case
    # we need to operate on that same instance of the account object.  Only load a new instance
    # if we don't get one passed in.
    if account is None:
        account = Account.objects.filter(id=account_id).first()
    if account.has_stripe():
            stripe_customer = account.get_stripe_customer()
    else:
        stripe_customer = stripe.Customer.create(
            description='Account %s' % account.account_name()
        )
        account.stripe_customer_id = stripe_customer.id
        account.save()

    skipCreate=False
    # first, make sure the account we are adding isn't already in stripe.  If it is, we need to just
    # set it.
    for existing in stripe_customer.bank_accounts.data:
        if routing is not None and (existing.routing_number == routing and existing.last4 == last4):
            # don't create, just put in our db.
            skipCreate=True
            stripe_bank_account=existing
            break

    if not skipCreate:
        try:
            stripe_bank_account = stripe_customer.bank_accounts.create(bank_account=token)
        except Exception as e:
            errors = []
            errors.append("There was an error adding this bank account.")
            raise CardException(errors)

    bank_account = account.get_bank_account()

    if bank_account is None:
        billing_payment_method = BillingPaymentMethod.objects.create_payment_method(account,BillingPaymentMethod.PAYMENT_ACH,nickname)
        bank_account = BankAccount(account=account,billing_payment_method=billing_payment_method)

    bank_account.update_from_stripe_bank_account(stripe_bank_account)

    bank_account.save()
    return bank_account
