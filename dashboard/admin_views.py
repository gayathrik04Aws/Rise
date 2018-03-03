from django.views.generic import TemplateView
from django.utils import timezone

import pytz
import arrow
from dateutil import tz
from datetime import datetime, timedelta
from django.db.models import Sum,F,FloatField

from accounts.models import User
from accounts.mixins import LoginRequiredMixin, PermissionRequiredMixin, StaffRequiredMixin
from flights.models import Flight, Airport, Plane,FlightReservation,Passenger,FlightWaitlist
from django.db.models import Count


class AdminDashboardView(LoginRequiredMixin, StaffRequiredMixin, PermissionRequiredMixin, TemplateView):
    """
    Admin dashboard page
    """

    permission_required = 'accounts.can_view_flights'
    template_name = 'dashboard/admin_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super(AdminDashboardView, self).get_context_data(**kwargs)

        start = arrow.utcnow().floor('day')
        start = start + timedelta(0, 0, 0, 0, 0, 6, 0)

        x = datetime(datetime.now().year, 1, 1, 0, 0, 0, tzinfo=pytz.timezone('US/Central'))  # Jan 1 of this year
        y = datetime.now(pytz.timezone('US/Central'))

        # RISE-480.  The previous code was starting the new day based on UTC clock, so at 6-7pm it was looking at the next day
        # need to set the start day based on CST.  During DST we are 5 hrs behind, otherwise 6.

        nowhour = arrow.utcnow().floor('hour')
        hour = nowhour.hour
        cstoffset = 6

        # if DST is in effect, their offsets will be different
        if not (y.utcoffset() == x.utcoffset()):
            cstoffset=5
            start = start - timedelta(0, 0, 0, 0, 0, 1, 0)

        # if it is late evening, i.e. already tomorrow in UTC, then we have to subtract a day to view current day in CST.
        if hour - cstoffset < 0:
            start = start - timedelta(1,0,0,0,0,0,0)

        end = start.replace(hours=24)
        flight_status_choices = [Flight.STATUS_ON_TIME,Flight.STATUS_DELAYED,Flight.STATUS_IN_FLIGHT]

        todays_flights = Flight.objects.select_related('plane', 'origin', 'destination', 'route_time', 'pilot')
        #retrieve all flights scheduled for today except the cancelled flights
        todays_flights = todays_flights.filter(departure__gte=start.datetime,
            departure__lt=end.datetime,status__in=flight_status_choices).order_by('departure')

        #total flights scheduled for today
        todays_flights_count = todays_flights.count()

        flight_reservation_status_choices= [FlightReservation.STATUS_PENDING ,FlightReservation.STATUS_ANYWHERE_PENDING,
                                     FlightReservation.STATUS_RESERVED,FlightReservation.STATUS_CHECKED_IN,FlightReservation.STATUS_COMPLETE]

        todays_flight_reservations = FlightReservation.objects.filter(flight_id__in=todays_flights,status__in=flight_reservation_status_choices)
        #members that are scheduled for today
        members_flown_today = Passenger.objects.filter(flight_reservation_id__in = todays_flight_reservations, checked_in=1).values('user_id').distinct().count()
        todays_total_duration = todays_flights.filter(status=Flight.STATUS_COMPLETE).aggregate(Sum('duration'))
        todays_total_hours = 0
        #total hours scheduled for today
        if todays_total_duration is not None and todays_total_duration.get('duration__sum') is not None:
            todays_total_hours = todays_total_duration.get('duration__sum')/60.0

        #today_flight_cost_dict = todays_flight_reservations.aggregate(total=Sum((F('cost')-F('anywhere_refund_paid')),output_field=FloatField()))

        #total flight cost for today
        #today_flight_cost = 0.0
        #if today_flight_cost_dict is not None and today_flight_cost_dict.get('total') is not None:
            #today_flight_cost = today_flight_cost_dict.get('total')

        yesterday = start - timedelta(days=1)
        yesterday_start = yesterday.floor('day')
        yesterday_end = yesterday_start.replace(hours=24)

        yesterdays_flights = Flight.objects.filter(departure__gte=yesterday_start.datetime,
            departure__lt=yesterday_end.datetime)
        yesterdays_flight_count = yesterdays_flights.count()
        on_time_yesterday = len([flight for flight in yesterdays_flights if flight.completed_on_time()])

        yesterday_flight_reservations = FlightReservation.objects.filter(flight_id__in=yesterdays_flights,status=FlightReservation.STATUS_COMPLETE)
        # total members that were flown yesterday
        members_flows_prev_day = Passenger.objects.filter(flight_reservation_id__in = yesterday_flight_reservations, checked_in=1).values('user_id').distinct().count()

        airports = Airport.objects.all()
        planes = Plane.objects.all()

        total_duration = yesterdays_flights.filter(status=Flight.STATUS_COMPLETE).aggregate(Sum('duration'))
        total_hours = 0
        #total hours for previous day
        if total_duration is not None and total_duration.get('duration__sum') is not None:
            total_hours = total_duration.get('duration__sum')/60.0

        month_start = start.floor('month')
        #month to date flights that were in completed status
        month_day_flights = Flight.objects.filter(departure__gte=month_start.datetime,
            departure__lt=start.datetime,status=Flight.STATUS_COMPLETE)
        #total number of flights till month to date
        month_day_flights_count = month_day_flights.count()

        total_month_day_duration = month_day_flights.aggregate(Sum('duration'))
        total_month_day_hours = 0
        #total number of hours the flight flew till month to date
        if total_month_day_duration is not None and total_month_day_duration.get('duration__sum') is not None:
            total_month_day_hours = total_month_day_duration.get('duration__sum')/60.0

        month_day_flight_reservations = FlightReservation.objects.filter(flight_id__in=month_day_flights,status=FlightReservation.STATUS_COMPLETE)
        #month_day_flight_cost_dict = month_day_flight_reservations.aggregate(total=Sum((F('cost')-F('anywhere_refund_paid')),output_field=FloatField()))
        #total cost till month to date
        #month_day_flight_cost = F(0.0)
        #if month_day_flight_cost_dict is not None and month_day_flight_cost_dict.get('total') is not None:
            #month_day_flight_cost = month_day_flight_cost_dict.get('total')
        #total no of members flown till month to date
        month_day_members= Passenger.objects.filter(flight_reservation_id__in = month_day_flight_reservations, checked_in=1).values('user_id').distinct().count()

        idlist = todays_flights.values_list('id',flat=True)
        flightwaitlist = FlightWaitlist.objects.filter(flight_id__in=idlist,status=FlightWaitlist.STATUS_WAITING).\
            values('flight_id').annotate(Count('id')).order_by()
        waitlistdict={}
        for key in flightwaitlist:
            waitlistdict[key.get('flight_id')]=key.get('id__count')
        context.update({
            'waitlist':waitlistdict,
            'todays_flights': todays_flights,
            'members_flows_prev_day':members_flows_prev_day,
            'yesterdays_flight_count': yesterdays_flight_count,
            'on_time_yesterday': on_time_yesterday,
            'airports': airports,
            'planes': planes,
            'total_hours':total_hours,
            'todays_flights_count':todays_flights_count,
            'members_flown_today':members_flown_today,
            'todays_total_hours':todays_total_hours,
            'month_day_flights_count':month_day_flights_count,
            'total_month_day_hours':total_month_day_hours,
            'month_day_members':month_day_members,
           # 'month_day_flight_cost':month_day_flight_cost,
           # 'today_flight_cost':today_flight_cost

        })

        return context

    def is_dst (self):
        """Determine whether or not Daylight Savings Time (DST)
        is currently in effect"""

        x = datetime(datetime.now().year, 1, 1, 0, 0, 0, tzinfo=pytz.timezone('US/Central')) # Jan 1 of this year
        y = datetime.now(pytz.timezone('US/Central'))

        # if DST is in effect, their offsets will be different
        return not (y.utcoffset() == x.utcoffset())
