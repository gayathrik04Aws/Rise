from __future__ import absolute_import

from celery import shared_task

from .models import Charge


@shared_task
def send_receipt_email(charge_id):
    charge = Charge.objects.get(id=charge_id)
    charge.send_receipt_email()
