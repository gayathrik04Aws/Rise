from django.utils.functional import cached_property
from django.shortcuts import redirect

from .mixins import BaseReservationMixin
from .models import FlightWaitlist


class AdminReservationMixin(BaseReservationMixin):
    """
    Mixin for accessing reservation related data when booking a reservation through the admin interface
    """
    redirect_name = 'admin_list_waitlist'

    def dispatch(self, request, *args, **kwargs):
        """
        if auto renew is on, renew on any request

        if reservation is required, redirect if None
        """

        # Not sure we need any of this
        # if self.require_permissions:
        #     user = self.booking_user or request.user
        #
        #     if not user.has_perm('accounts.can_fly'):
        #         if not user.has_perm('accounts.can_book_team'):
        #             messages.error(request, 'You do not have permission to book a flight.')
        #             return redirect('admin_dashboard')
        #
        #         return redirect('book_team_member')

        if self.reservation_required:
            if self.reservation is None:
                return redirect(self.redirect_name)

        # Do we need to do this in the admin?
        if self.auto_renew and self.reservation is not None:
            self.reservation.renew()

        return super(AdminReservationMixin, self).dispatch(request, *args, **kwargs)

    def clear_all(self):
        """
        Clears all session related reservation variables
        """
        super(AdminReservationMixin, self).clear_all()
        self.clear_flight_waitlist()

    @cached_property
    def flight_waitlist(self):
        """
        Returns the FlightWaitlist this reservation is being generated from, if any.
        """
        flight_waitlist_id = self.request.session.get('flight_waitlist_id')
        if flight_waitlist_id is None:
            return None

        return next(iter(FlightWaitlist.objects.filter(id=flight_waitlist_id).select_related('user', 'flight')), None)

    def set_flight_waitlist(self, flight_waitlist):
        """
        Set the flight waitlist object.
        """
        self.flight_waitlist = flight_waitlist
        if flight_waitlist is None:
            self.clear_flight_waitlist()
        else:
            self.request.session['flight_waitlist_id'] = flight_waitlist.id

    def clear_flight_waitlist(self):
        """
        Clears the flight waitlist from the session
        """
        if 'flight_waitlist_id' in self.request.session:
            del self.request.session['flight_waitlist_id']
