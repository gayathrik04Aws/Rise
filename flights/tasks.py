from __future__ import absolute_import

from celery import shared_task

from .models import Flight


@shared_task
def send_marketing_flight_email(flight_id):
    flight = Flight.objects.get(id=flight_id)
    flight.send_marketing_flight_email()
