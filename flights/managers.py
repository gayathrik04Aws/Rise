from django.db import models

from collections import OrderedDict
import arrow


class FlightSearchManager(models.Manager):
    """
    A queryset manager for centralizing flight search logic
    """

    def get_availability_for_date_range(self, origin, start_date, end_date, userprofile, companion_count=0, destination=None, include_rise_anywhere=False):
        """
        Returns availability information for a given date range (most likely month based).

        origin: the origin airport
        destination: destination airport
        start_date: The start datetime of the date range, inclusive
        end_date: The end datetime of the date range, inclusive
        user: The user that the flight is being booked for
        companion_count: The number of companions requested for this flight

        Returns an ordered dictionary based on flight departure date. The keys are the date for the results and the
        values are another dictionary. The result values contain total number of flight, number of full flights, number
        of unavailable flights, number of available flights along with boolean values for no flights, all flights are
        full, all flights unavailble, and any flights available. See code below for key names.
        """
        results = OrderedDict()

        # get the calendar day range
        begin_days = arrow.get(start_date).floor('day')
        end_days = arrow.get(end_date).floor('day')
        day_range = arrow.Arrow.range('day', begin_days, end_days)

        # build the result structure for each day
        for day in day_range:
            results[day.date()] = {
                'total': 0,
                'full': 0,
                'unavailable': 0,
                'available': 0,
                'no_flights': True,
                'is_full': False,
                'is_unavailable': False,
                'is_available': False,
            }

        # get all of the flights
        if include_rise_anywhere:
            flights = self.get_queryset().filter(origin=origin, departure__gte=start_date, departure__lte=end_date, status__in=(self.model.STATUS_ON_TIME, self.model.STATUS_DELAYED,)).order_by('departure')
        else:
            flights = self.get_queryset().filter(origin=origin, departure__gte=start_date, departure__lte=end_date, status__in=(self.model.STATUS_ON_TIME, self.model.STATUS_DELAYED,)).exclude(flight_type="A").order_by('departure')

        # also filter on destination if provided
        if destination is not None:
            flights = flights.filter(destination=destination)

        # iterate through flights to count them up
        for flight in flights:
            # see if this flight is account restricted
            account_available = flight.check_account_restriction(userprofile)
            # if so, we dont want to export account restricted flights to users that cannot book them
            if not account_available:
                continue

            # see if this flight is VIP restricted
            vip_available = flight.check_vip(userprofile)
            # if so, we dont want to export VIP restricted flights to users that cannot book them
            if not vip_available:
                continue

            # see if this flight is Founder restricted
            founder_available = flight.check_founder(userprofile)
            # if so, we dont want to export Founder restricted flights to users that cannot book them
            if not founder_available:
                continue

            # see if the user is allowed to book this flight (can_book_promo, etc)
            user_allowed = flight.check_user_permissions(userprofile, companion_count)

            # if not allowed, do not show
            if not user_allowed:
                continue

            # results dict key
            flight_day = arrow.get(flight.departure).to(origin.timezone).date()

            # increment total flights for day possible
            results[flight_day]['total'] += 1

            # check to see if the flight is full
            full = flight.is_flight_full(userprofile, companion_count)

            # if full, add it to the results, and move on
            if full:
                results[flight_day]['full'] += 1
                continue

            # if the flight is already booked by a user, mark it as unavailable for now
            if flight.is_booked_by_user(userprofile):
                results[flight_day]['unavailable'] += 1

            # see if the user's plan allows them to book this flight
            plan_available = flight.check_plan_restrictions(userprofile, companion_count) and flight.check_plan_seat_restrictions(userprofile, (1 + companion_count))

            # if the flight is not available based on the user's plan
            if not plan_available:
                results[flight_day]['unavailable'] += 1
                continue

            # All other checks passed, so this flight is available to book
            results[flight_day]['available'] += 1

        # update boolean result values per day
        for day in results:
            values = results[day]
            # if there are no flights for the given day
            values['no_flights'] = values['total'] == 0
            # if all flights are full
            values['is_full'] = values['total'] == values['full']
            # if all flights are unavailable
            values['is_unavailable'] = values['total'] == values['unavailable']
            # if there are any flights available
            values['is_available'] = values['available'] > 0

        return results

    def get_flights_for_date(self, origin, flight_date, userprofile, companion_count=0, destination=None, include_rise_anywhere=False, user_is_not_flying=False):
        """
        Return flights for the given date and origin (optionally destination) with given user and companion count
        """
        results = []

        day_start = arrow.get(flight_date, origin.timezone)
        day_end = day_start.replace(hours=24)

        # if now is between start and end, start at now
        now = arrow.now(origin.timezone)
        if day_start < now < day_end:
            day_start = now

        # get all of the flights
        if include_rise_anywhere:
            flights = self.get_queryset().filter(origin=origin, departure__gte=day_start.datetime, departure__lte=day_end.datetime, status__in=(self.model.STATUS_ON_TIME, self.model.STATUS_DELAYED,)).order_by('departure')
        else:
            flights = self.get_queryset().filter(origin=origin, departure__gte=day_start.datetime, departure__lte=day_end.datetime, status__in=(self.model.STATUS_ON_TIME, self.model.STATUS_DELAYED,)).exclude(flight_type="A").order_by('departure')

        # also filter on destination if provided
        if destination is not None:
            flights = flights.filter(destination=destination)

        # iterate through flights to count them up
        for flight in flights:
            # see if this flight is account restricted
            account_available = flight.check_account_restriction(userprofile)
            # if so, we dont want to export account restricted flights to users that cannot book them
            if not account_available:
                continue

            # see if this flight is VIP restricted
            vip_available = flight.check_vip(userprofile)
            # if so, we dont want to export VIP restricted flights to users that cannot book them
            if not vip_available:
                continue

            # see if this flight is Founder restricted
            founder_available = flight.check_founder(userprofile)
            # if so, we dont want to export Founder restricted flights to users that cannot book them
            if not founder_available:
                continue

            # see if the user is allowed to book this flight (can_book_promo, etc)
            user_allowed = flight.check_user_permissions(userprofile, companion_count)

            # if not allowed, do not show
            if not user_allowed:
                continue

            # see if the user is allowed to book this flight (can_book_promo, etc)
            user_allowed = flight.check_user_permissions(userprofile, companion_count)

            # if not allowed, do not show
            if not user_allowed:
                continue

            # check to see if the flight is full
            flight.is_full = flight.is_flight_full(userprofile, companion_count)

            # check to see if this flight is booked by the user
            if not user_is_not_flying:
                flight.is_booked = flight.is_booked_by_user(userprofile)

            # see if the user's plan allows them to book this flight
            flight.is_available = flight.check_plan_restrictions(userprofile, companion_count) and flight.check_plan_seat_restrictions(userprofile, (1 + companion_count))

            results.append(flight)

        return results

    def get_similar_flights(self, flight, userprofile, companion_count, include_rise_anywhere=False):
        '''
        Retrieves a list of flights based on a given flight for the next two weeks.
        It tries to filter flight results on the flight's RouteTime, but if none, the results
        will show all similar flights for the next two weeks.
        '''
        origin = flight.origin
        destination = flight.destination
        start_date = arrow.now()
        end_date = start_date.replace(weeks=+2)
        if companion_count is None:
            companion_count = flight_reservation.get_companion_count()

        results = []

        # get all of the flights
        if include_rise_anywhere:
            flights = self.get_queryset().filter(origin=origin, destination=destination, departure__gte=start_date.datetime, departure__lte=end_date.datetime, status__in=(self.model.STATUS_ON_TIME, self.model.STATUS_DELAYED,)).order_by('departure')
        else:
            flights = self.get_queryset().filter(origin=origin, destination=destination, departure__gte=start_date.datetime, departure__lte=end_date.datetime, status__in=(self.model.STATUS_ON_TIME, self.model.STATUS_DELAYED,)).exclude(flight_type="A").order_by('departure')

        try:
            route_time = flight.route_time
            flights = flights.filter(route_time=route_time)
        except AttributeError:
            pass

        # iterate through flights to count them up
        for flight in flights:
            # see if this flight is account restricted
            account_available = flight.check_account_restriction(userprofile)
            # if so, we dont want to export account restricted flights to users that cannot book them
            if not account_available:
                continue

            # see if the user is allowed to book this flight (can_book_promo, etc)
            user_allowed = flight.check_user_permissions(userprofile, companion_count)

            # if not allowed, do not show
            if not user_allowed:
                continue

            # check to see if the flight is full
            flight.is_full = flight.is_flight_full(userprofile, companion_count)

            # check to see if this flight is booked by the user
            flight.is_booked = flight.is_booked_by_user(userprofile)

            # see if the user's plan allows them to book this flight
            flight.is_available = flight.check_plan_restrictions(userprofile, companion_count) and flight.check_plan_restrictions(user, companion_count)

            results.append(flight)

        return results


    def get_single_flight(self, flight, userprofile, companion_count):
        '''
        Retrieves a list of one flight based on the given flight for making a reservation on it
        '''
        start_date = arrow.now()
        if companion_count is None:
            companion_count = flight_reservation.get_companion_count()

        results = []

        # get the flight if it's reservable
        flights = self.get_queryset().filter(id=flight.pk, departure__gte=start_date.datetime, status__in=(self.model.STATUS_ON_TIME, self.model.STATUS_DELAYED,))

        # iterate through flights to count them up
        for flight in flights:
            # see if this flight is account restricted
            account_available = flight.check_account_restriction(userprofile)
            # if so, we dont want to export account restricted flights to users that cannot book them
            if not account_available:
                continue

            # see if the user is allowed to book this flight (can_book_promo, etc)
            user_allowed = flight.check_user_permissions(userprofile, companion_count)

            # if not allowed, do not show
            if not user_allowed:
                continue

            # check to see if the flight is full
            flight.is_full = flight.is_flight_full(userprofile, companion_count)

            # check to see if this flight is booked by the user
            flight.is_booked = flight.is_booked_by_user(userprofile)

            # see if the user's plan allows them to book this flight
            flight.is_available = flight.check_plan_restrictions(userprofile, companion_count) and flight.check_plan_restrictions(userprofile, companion_count)

            results.append(flight)

        return results
