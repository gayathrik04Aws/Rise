from django.views.generic import View,  FormView
from django.http import HttpResponse
from django.contrib import messages
import unicodecsv
import arrow
from django.core.urlresolvers import reverse, reverse_lazy

from .models import Charge
from accounts.mixins import StaffRequiredMixin, PermissionRequiredMixin
from mixins import TestHarnessAllowedMixin
from admin_forms import TransactionHarnessForm

class ExportChargesView(StaffRequiredMixin, PermissionRequiredMixin, View):
    """
    A view to export accounts to CSV
    """

    permission_required = 'accounts.can_view_members'

    def get(self, request, *args, **kwargs):
        charges = Charge.objects.all().select_related()

        date_format = 'YYYY-MM-DD HH:mm:ss ZZ'

        # Create the HttpResponse object with the appropriate CSV header.
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="charges.csv"'

        writer = unicodecsv.writer(response)
        writer.writerow(['Account ID', 'Account Name', 'Payment Method', 'Payment Instrument', 'Vault ID', 'Amount',
            'Amount Refunded', 'Description', 'Status', 'Captured', 'Paid', 'Refunded', 'Failure Code',
            'Failure Message', 'Created On', 'Created By'])

        for charge in charges:
            writer.writerow([
                str(charge.account.id) if charge.account else '',
                charge.account.account_name() if charge.account else '',
                charge.get_payment_method_display(),
                charge.card or charge.bank_account or '',
                charge.vault_id,
                charge.amount,
                charge.amount_refunded,
                charge.description,
                charge.status,
                'Yes' if charge.captured else 'No',
                'Yes' if charge.paid else 'No',
                'Yes' if charge.refunded else 'No',
                charge.failure_code,
                charge.failure_message,
                arrow.get(charge.created).format(date_format),
                charge.created_by.get_full_name() if charge.created_by else '',
            ])

        return response


class TransactionTestHarnessView(TestHarnessAllowedMixin, StaffRequiredMixin, FormView):
    form_class = TransactionHarnessForm
    template_name = 'billing/test_transaction_harness.html'
    permission_required = 'accounts.can_charge_members'
    success_url = reverse_lazy("admin_test_transaction_harness")

    def get_context_data(self, **kwargs):
        context = super(TransactionTestHarnessView,self).get_context_data(**kwargs)
        context["gothere"]="yesidid"
        return context

    def form_valid(self, form):
        result = form.update_status()
        if not result:
            messages.error(self.request, "Unable to update status")
            return super(TransactionTestHarnessView, self).form_valid(form)
        messages.success(self.request, "Status Updated!")
        return super(TransactionTestHarnessView, self).form_valid(form)
