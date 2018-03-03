from django import forms
from models import Charge
import braintree

class TransactionHarnessForm(forms.Form):
    STATUS_SETTLED = 'Settled'
    STATUS_CONFIRMED = 'Confirmed'

    STATUS_CHOICES = (
        (STATUS_SETTLED, 'Settled'),
        (STATUS_CONFIRMED, 'Confirmed'),
    )


    charge_id = forms.CharField(max_length=20)
    status = forms.ChoiceField(choices=STATUS_CHOICES)

    def update_status(self):
        charge = Charge.objects.filter(id=self.cleaned_data["charge_id"]).first()
        if charge:
            transaction = charge.get_transaction()
            if transaction:
                testing_gateway = braintree.TestingGateway(braintree.Configuration.gateway())
                if self.cleaned_data["status"] == self.STATUS_SETTLED:
                    testing_gateway.settle_transaction(transaction.id)
                    updated_transaction = braintree.Transaction.find(transaction.id)
                    if updated_transaction.status == braintree.Transaction.Status.Settled:
                        return True
                elif self.cleaned_data["status"] == self.STATUS_CONFIRMED:
                    testing_gateway.settlement_confirm_transaction(transaction.id)
                    updated_transaction = braintree.Transaction.find(transaction.id)
                    if updated_transaction.status == braintree.Transaction.Status.SettlementConfirmed:
                        return True
        return False
