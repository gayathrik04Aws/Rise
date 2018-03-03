from django.conf import settings
import datetime
from decimal import Decimal

class AnywherePricingMixin(object):

    @property
    def full_flight_price(self):
        if hasattr(self, "full_flight_cost"):
            return self.full_flight_cost
        return 0

    @property
    def two_seat_price(self):
        return self.full_flight_price / 2

    @property
    def three_seat_price(self):
        return self.full_flight_price / 3

    @property
    def four_seat_price(self):
        return self.full_flight_price / 4

    @property
    def five_seat_price(self):
        return self.full_flight_price / 5

    @property
    def six_seat_price(self):
        return self.full_flight_price / 6

    @property
    def seven_seat_price(self):
        return self.full_flight_price / 7

    @property
    def eight_seat_price(self):
        return self.full_flight_price / 8

    def other_seat_price(self, num_seats):
        if num_seats > 0:
            return self.full_flight_price / num_seats
        return self.full_flight_price

    # Rise-157 Use this to calculate per-seat cost for actual sold seats on a leg.
    def leg_per_seat_price(self, leg_price, num_seats):
        if num_seats > 0:
            return leg_price / num_seats
        return leg_price

    def estimate_leg_cost(self, leg_number, is_round_trip, outbound_route, return_route, outbound_date, return_date):
        """
        Logic:
        ALL Rise Anywhere flight cost is lumped into outbound leg.
        Leg2 = 0.
        This is to avoid refund issues where a cancelled second leg ends up refunding passengers.
         Add margin to leg base cost
        Then use either one way, short-turn RT, or long-turn RT multiplier depending on time delay between legs.

        Args:
            leg_number:
            is_round_trip:
            outbound_route:
            return_route:
            outbound_date:
            return_date:

        Returns:

        """
        if outbound_route is None:
            return 0

        if is_round_trip:
            if leg_number == 2:
                return 0
            else:
                baselegcost = outbound_route.cost
            delta = return_date - outbound_date
            deltahours = delta.days * 24
            if deltahours <= settings.SHORT_TURN_TIME_HRS:
               multiplier = settings.SHORT_TURN_COST_MULTIPLIER
            else:
                multiplier = settings.LONG_TURN_COST_MULTIPLIER
        else:
            baselegcost = outbound_route.cost
            multiplier = settings.ONE_WAY_COST_MULTIPLIER

        costwithmargin = (baselegcost *  settings.RISE_MARGIN) + baselegcost
        return format(costwithmargin * multiplier,'.2f')

    def estimate_total_flight_cost(self, is_round_trip, outbound_route, return_route, outbound_date, return_date):
        """
        Logic:
        Add margin to leg base cost
        Then use either one way, short-turn RT, or long-turn RT multiplier depending on time delay between legs.

        Args:
            is_round_trip:
            outbound_route:
            return_route:
            outbound_date:
            return_date:

        Returns:

        """
        # saw an NRE in production on outbound route;  this only would happen if no route defined, but we should handle gracefully
        if outbound_route is None:
            return 0

        baseprice = outbound_route.cost
        if is_round_trip:
            if return_route is None:
                return -1
            else:
                delta = return_date - outbound_date
                deltahours  = delta.days * 24
                if deltahours <= settings.SHORT_TURN_TIME_HRS:
                   multiplier = settings.SHORT_TURN_COST_MULTIPLIER
                else:
                    multiplier = settings.LONG_TURN_COST_MULTIPLIER
        else:
            multiplier = settings.ONE_WAY_COST_MULTIPLIER
        basewithmargin = (baseprice * settings.RISE_MARGIN) + baseprice
        return format(basewithmargin * multiplier,'.2f')
