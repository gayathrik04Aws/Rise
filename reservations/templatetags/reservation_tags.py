from django import template
from billing.models import ChargeRefund

register = template.Library()


@register.filter(name='get_refund_id')
def get_refund_id(charge_id):
    refund = ChargeRefund.objects.filter(charge_id=charge_id).first()
    if refund:
        return refund.id
    return "N/A"
