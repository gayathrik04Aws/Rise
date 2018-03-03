from django.test import TestCase
from django.contrib.auth.models import Permission

from accounts.factories import UserFactory, CorporateAccountFactory, AccountFactory, StaffUserFactory
from .factories import FlightFactory, FlightPlanRestrictionFactory, FlightPlanSeatRestrictionFactory
from reservations.factories import FlightReservationFactory, ReservationFactory
from billing.factories import PlanFactory
from .models import Flight
from reservations.models import FlightReservation

import arrow


class FlightTestCase(TestCase):

    def setUp(self):
        pass

    def test_full_capacity(self):
        user = UserFactory()
        flight = FlightFactory.build(seats_available=0)

        self.assertTrue(flight.is_flight_full(user, companion_count=0), 'Completely full flight')

        flight = FlightFactory.build(seats_available=1)

        self.assertTrue(flight.is_flight_full(user, companion_count=1), 'Full with companion')

        flight = FlightFactory.build(seats_available=2)

        self.assertTrue(flight.is_flight_full(user, companion_count=2), 'Full with companions')

    def test_companions_full(self):
        user = UserFactory()
        flight = FlightFactory.build(seats_total=8, seats_available=2, seats_companion=4, max_seats_companion=4)

        self.assertTrue(flight.is_flight_full(user, companion_count=1), 'Too many companions')

        flight = FlightFactory.build(seats_total=8, seats_available=2, seats_companion=3)

        self.assertTrue(flight.is_flight_full(user, companion_count=2), 'Too many companions')

    def test_corporation_full(self):
        corp_account = CorporateAccountFactory()
        corp_user = UserFactory(account=corp_account)

        flight = FlightFactory(seats_total=8, seats_available=4, max_seats_corporate=4)

        reservation = ReservationFactory.create(account=corp_account)
        FlightReservationFactory.create(reservation=reservation, flight=flight, passenger_count=1)
        self.assertFalse(flight.is_flight_full(corp_user), 'corp flight not full yet')
        FlightReservationFactory.create(reservation=reservation, flight=flight, passenger_count=1)
        self.assertFalse(flight.is_flight_full(corp_user), 'corp flight not full yet')
        FlightReservationFactory.create(reservation=reservation, flight=flight, passenger_count=1)
        self.assertFalse(flight.is_flight_full(corp_user), 'corp flight not full yet')
        FlightReservationFactory.create(reservation=reservation, flight=flight, passenger_count=1)
        self.assertTrue(flight.is_flight_full(corp_user), 'too many of same corp on plane')

    def test_plan_restrictions(self):
        corp_account = CorporateAccountFactory.create()
        corp_user = UserFactory.create(account=corp_account)

        plan_1 = PlanFactory()
        plan_2 = PlanFactory()
        plan_3 = PlanFactory()

        account_1 = AccountFactory(plan=plan_1)
        account_2 = AccountFactory(plan=plan_2)
        account_3 = AccountFactory(plan=plan_3)

        user_1 = UserFactory(account=account_1)
        user_2 = UserFactory(account=account_2)
        user_3 = UserFactory(account=account_3)

        flight = FlightFactory(departure=arrow.now().replace(days=+12).datetime)

        self.assertTrue(flight.check_plan_restrictions(corp_user), 'always allow corp users')

        self.assertTrue(flight.check_plan_restrictions(user_1), 'no plan restrictions')
        self.assertTrue(flight.check_plan_restrictions(user_2), 'no plan restrictions')
        self.assertTrue(flight.check_plan_restrictions(user_3), 'no plan restrictions')

        FlightPlanRestrictionFactory(flight=flight, plan=plan_1, days=2)
        FlightPlanRestrictionFactory(flight=flight, plan=plan_2, days=12)
        FlightPlanRestrictionFactory(flight=flight, plan=plan_3, days=16)

        self.assertTrue(flight.check_plan_restrictions(corp_user), 'always allow corp users')

        self.assertFalse(flight.check_plan_restrictions(user_1), 'only 2 days out')
        self.assertTrue(flight.check_plan_restrictions(user_2), 'just now')
        self.assertTrue(flight.check_plan_restrictions(user_3), 'been good')

        flight.departure = arrow.now().replace(days=+13).datetime
        flight.save()

        self.assertTrue(flight.check_plan_restrictions(corp_user), 'always allow corp users')

        self.assertFalse(flight.check_plan_restrictions(user_1), 'only 2 days out')
        self.assertFalse(flight.check_plan_restrictions(user_2), 'just now')
        self.assertTrue(flight.check_plan_restrictions(user_3), 'been good')

        flight.departure = arrow.now().replace(days=+16).datetime
        flight.save()

        self.assertTrue(flight.check_plan_restrictions(corp_user), 'always allow corp users')

        self.assertFalse(flight.check_plan_restrictions(user_1), 'only 2 days out')
        self.assertFalse(flight.check_plan_restrictions(user_2), 'just now')
        self.assertTrue(flight.check_plan_restrictions(user_3), 'been good')

        flight.departure = arrow.now().replace(days=+17).datetime
        flight.save()

        self.assertTrue(flight.check_plan_restrictions(corp_user), 'always allow corp users')

        self.assertFalse(flight.check_plan_restrictions(user_1), 'only 2 days out')
        self.assertFalse(flight.check_plan_restrictions(user_2), 'just now')
        self.assertFalse(flight.check_plan_restrictions(user_3), 'been good')

    def test_plan_seat_restrictions(self):
        plan_1 = PlanFactory()
        plan_2 = PlanFactory()
        plan_3 = PlanFactory()

        account_1 = AccountFactory(plan=plan_1)
        account_2 = AccountFactory(plan=plan_2)
        account_3 = AccountFactory(plan=plan_3)

        user_1 = UserFactory(account=account_1)
        user_2 = UserFactory(account=account_2)
        user_3 = UserFactory(account=account_3)

        flight = FlightFactory(departure=arrow.now().replace(days=+12).datetime, seats_total=8)

        self.assertTrue(flight.check_plan_seat_restrictions(user_1, 1), 'no plan seat restrictions')
        self.assertTrue(flight.check_plan_seat_restrictions(user_2, 1), 'no plan seat restrictions')
        self.assertTrue(flight.check_plan_seat_restrictions(user_3, 1), 'no plan seat restrictions')

        FlightPlanSeatRestrictionFactory(flight=flight, plan=plan_1, seats=1)
        FlightPlanSeatRestrictionFactory(flight=flight, plan=plan_2, seats=2)
        FlightPlanSeatRestrictionFactory(flight=flight, plan=plan_3, seats=3)

        self.assertTrue(flight.check_plan_seat_restrictions(user_1, 1), 'seats still available for plan')
        self.assertTrue(flight.check_plan_seat_restrictions(user_2, 1), 'seats still available for plan')
        self.assertTrue(flight.check_plan_seat_restrictions(user_3, 1), 'seats still available for plan')

        account_4 = AccountFactory(plan=plan_1)
        account_5 = AccountFactory(plan=plan_2)
        account_6 = AccountFactory(plan=plan_3)

        reservation_4 = ReservationFactory(account=account_4)
        FlightReservationFactory.create(reservation=reservation_4, flight=flight, passenger_count=1)
        reservation_4.reserve()

        self.assertFalse(flight.check_plan_seat_restrictions(user_1, 1), 'No seats still available for plan')

        reservation_5 = ReservationFactory(account=account_5)
        FlightReservationFactory.create(reservation=reservation_5, flight=flight, passenger_count=2)
        reservation_5.reserve()

        self.assertFalse(flight.check_plan_seat_restrictions(user_2, 1), 'No seats still available for plan')

        reservation_6 = ReservationFactory(account=account_6)
        FlightReservationFactory.create(reservation=reservation_6, flight=flight, passenger_count=3)
        reservation_6.reserve()

        self.assertFalse(flight.check_plan_seat_restrictions(user_3, 1), 'No seats still available for plan')

    def test_account_restrictions(self):
        corp_account = CorporateAccountFactory.create()
        corp_user = UserFactory.create(account=corp_account)
        account = AccountFactory.create()
        user = UserFactory.create(account=account)

        flight = FlightFactory()

        self.assertTrue(flight.check_account_restriction(corp_user), 'no account restrictriction')
        self.assertTrue(flight.check_account_restriction(user), 'no account restrictriction')

        flight.account_restriction.add(corp_account)

        self.assertTrue(flight.check_account_restriction(corp_user), 'corporate only flight')
        self.assertFalse(flight.check_account_restriction(user), 'corporate only flight')

        flight.account_restriction.add(account)
        self.assertTrue(flight.check_account_restriction(corp_user), 'corp and individual account good')
        self.assertTrue(flight.check_account_restriction(user), 'corp and individual account good')

    def test_check_user_permissions(self):
        account = AccountFactory.create()
        user_1 = UserFactory.create(account=account)
        user_2 = UserFactory.create(account=account)

        flight = FlightFactory.create()

        self.assertFalse(flight.check_user_permissions(user_1), 'no fly permissions')
        self.assertFalse(flight.check_user_permissions(user_2), 'no fly permissions')

        user_1.user_permissions.add(Permission.objects.get(codename='can_fly'))
        delattr(user_1, '_perm_cache')

        self.assertTrue(flight.check_user_permissions(user_1), 'can fly permissions')
        self.assertFalse(flight.check_user_permissions(user_2), 'no fly permissions')

        user_2.user_permissions.add(Permission.objects.get(codename='can_fly'))
        delattr(user_2, '_perm_cache')
        user_1.user_permissions.add(Permission.objects.get(codename='can_book_promo_flights'))
        delattr(user_1, '_perm_cache')

        promo_flight = FlightFactory.create(flight_type=Flight.TYPE_PROMOTION)

        self.assertTrue(flight.check_user_permissions(user_1), 'regular flight')
        self.assertTrue(flight.check_user_permissions(user_2), 'regular flight')

        self.assertTrue(promo_flight.check_user_permissions(user_1), 'promo flight')
        self.assertFalse(promo_flight.check_user_permissions(user_2), 'promo flight nope')


class AdminAddAirportViewTest(TestCase):
    def setUp(self):
        account = AccountFactory.create()
        self.user_1 = UserFactory.create(account=account)
        self.staff_1 = StaffUserFactory.create()

    def test_non_staff_access(self):
        self.client.login(username=self.user_1.email, password='password')
        response = self.client.get('/riseadmin/airport/add/')
        self.assertEqual(302, response.status_code)

    def test_staff_access(self):
        self.client.login(username=self.staff_1.email, password='password')
        response = self.client.get('/riseadmin/airport/add/')
        self.assertEqual(200, response.status_code)


class AdminAddPlaneViewTest(TestCase):
    def setUp(self):
        account = AccountFactory.create()
        self.user_1 = UserFactory.create(account=account)
        self.staff_1 = StaffUserFactory.create()

    def test_non_staff_access(self):
        self.client.login(username=self.user_1.email, password='password')
        response = self.client.get('/riseadmin/plane/add/')
        self.assertEqual(302, response.status_code)

    def test_staff_access(self):
        self.client.login(username=self.staff_1.email, password='password')
        response = self.client.get('/riseadmin/plane/add/')
        self.assertEqual(200, response.status_code)


class AdminAddFlightViewTest(TestCase):
    def setUp(self):
        account = AccountFactory.create()
        self.user_1 = UserFactory.create(account=account)
        self.staff_1 = StaffUserFactory.create()

    def test_non_staff_access(self):
        self.client.login(username=self.user_1.email, password='password')
        response = self.client.get('/riseadmin/flights/add/')
        self.assertEqual(302, response.status_code)

    def test_staff_access(self):
        self.client.login(username=self.staff_1.email, password='password')
        response = self.client.get('/riseadmin/flights/add/')
        self.assertEqual(200, response.status_code)


class AdminFlightListViewTest(TestCase):
    def setUp(self):
        account = AccountFactory.create()
        self.user_1 = UserFactory.create(account=account)
        self.staff_1 = StaffUserFactory.create()

    def test_non_staff_access(self):
        self.client.login(username=self.user_1.email, password='password')
        response = self.client.get('/riseadmin/flights/')
        self.assertEqual(302, response.status_code)

    def test_staff_access(self):
        self.client.login(username=self.staff_1.email, password='password')
        response = self.client.get('/riseadmin/flights/')
        self.assertEqual(200, response.status_code)


class AdminRouteListViewTest(TestCase):
    def setUp(self):
        account = AccountFactory.create()
        self.user_1 = UserFactory.create(account=account)
        self.staff_1 = StaffUserFactory.create()

    def test_non_staff_access(self):
        self.client.login(username=self.user_1.email, password='password')
        response = self.client.get('/riseadmin/routes/')
        self.assertEqual(302, response.status_code)

    def test_staff_access(self):
        self.client.login(username=self.staff_1.email, password='password')
        response = self.client.get('/riseadmin/routes/')
        self.assertEqual(200, response.status_code)


class AdminAddRouteListViewTest(TestCase):
    def setUp(self):
        account = AccountFactory.create()
        self.user_1 = UserFactory.create(account=account)
        self.staff_1 = StaffUserFactory.create()

    def test_non_staff_access(self):
        self.client.login(username=self.user_1.email, password='password')
        response = self.client.get('/riseadmin/routes/add/')
        self.assertEqual(302, response.status_code)

    def test_staff_access(self):
        self.client.login(username=self.staff_1.email, password='password')
        response = self.client.get('/riseadmin/routes/add/')
        self.assertEqual(200, response.status_code)
