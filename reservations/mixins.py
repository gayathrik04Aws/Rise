from django.utils.functional import cached_property
from django.shortcuts import redirect
from django.contrib import messages
from django.http import Http404
from django.conf import settings
from datetime import date

from announcements.models import AutomatedMessage
from .models import Reservation
from accounts.models import Account, User, UserProfile
from flights.models import Airport


class BaseReservationMixin(object):
    """
    A base class with common elements of ReservationMixin objects
    """
    auto_renew = True
    reservation_required = False
    redirect_name = 'book_from'
    require_permissions = True

    def get_context_data(self, **kwargs):
        context = super(BaseReservationMixin, self).get_context_data(**kwargs)

        context.update({
            'reservation': self.reservation,
            'origin_airport': self.origin_airport,
            'booking_date': self.booking_date,
            'booking_user': self.booking_user,
            'booking_userprofile': self.booking_userprofile
        })

        return context

    def clear_all(self):
        """
        Clears all session related reservation variables
        """
        self.clear_origin_airport()
        self.clear_booking_user()
        self.clear_booking_userprofile()
        self.clear_booking_date()
        self.clear_companion_count()
        self.clear_companions_only()
        self.clear_reservation()

    @cached_property
    def reservation(self):
        """
        returns the reservation if one, else None

        Note: cached property
        """
        pk = self.request.session.get('reservation_pk')
        if pk is None:
            return None
        return next(iter(Reservation.objects.filter(pk=pk)), None)

    def set_reservation(self, reservation):
        """
        Saves the reservation pk in the session
        """
        self.reservation = reservation
        self.request.session['reservation_pk'] = reservation.pk

    def clear_reservation(self):
        """
        Clears a reservation value from the session
        """
        if 'reservation_pk' in self.request.session:
            del self.request.session['reservation_pk']

    @cached_property
    def origin_airport(self):
        """
        returns the origin_airport if one, else None

        Note: cached property
        """
        pk = self.request.session.get('origin_airport_pk')
        if pk is None:
            return None
        return next(iter(Airport.objects.filter(pk=pk)), None)

    def set_origin_airport(self, origin_airport):
        """
        Saves the reservation pk in the session
        """
        self.origin_airport = origin_airport
        self.request.session['origin_airport_pk'] = origin_airport.pk

    def clear_origin_airport(self):
        """
        Clears a reservation value from the session
        """
        if 'origin_airport_pk' in self.request.session:
            del self.request.session['origin_airport_pk']

    @cached_property
    def booking_date(self):
        """
        returns the booking_date if one, else None

        Note: cached property
        """
        timetuple = self.request.session.get('booking_date')
        if timetuple is None:
            return None
        return date(*timetuple)

    def set_booking_date(self, booking_date):
        """
        Saves the reservation pk in the session
        """
        self.booking_date = booking_date
        if booking_date is None:
            self.clear_booking_date()
            return
        self.request.session['booking_date'] = booking_date.timetuple()[:3]

    def clear_booking_date(self):
        """
        Clears a reservation value from the session
        """
        if 'booking_date' in self.request.session:
            del self.request.session['booking_date']

    @cached_property
    def companion_count(self):
        """
        returns the reservation if one, else None

        Note: cached property
        """
        companion_count = self.request.session.get('companion_count', 0)
        return companion_count

    def set_companion_count(self, companion_count):
        """
        Saves the reservation pk in the session
        """
        self.companion_count = companion_count
        self.request.session['companion_count'] = companion_count

    @cached_property
    def companions_only(self):
        """
        returns whether the booking will NOT include the member making the booking

        Note: cached property
        """
        companions_only = self.request.session.get('companions_only', False)
        return companions_only

    def set_companions_only(self, companions_only):
        """
        Saves the reservation pk in the session
        """
        self.companions_only = companions_only
        self.request.session['companions_only'] = companions_only


    def clear_companion_count(self):
        """
        clears companion count from session
        """
        if 'companion_count' in self.request.session:
            del self.request.session['companion_count']


    def clear_companions_only(self):
        """
        clears companion count from session
        """
        if 'companions_only' in self.request.session:
            del self.request.session['companions_only']

    @cached_property
    def booking_user(self):
        """
        Returns the user that this reservation is actually for.

        Corporate accounts can allow users to book on behalf of other users.

        Defaults to the currently logged in user if no booking user set.
        """
        booking_user_id = self.request.session.get('booking_user_id')
        if booking_user_id is None:
            return self.request.user

        booking_user = next(iter(User.objects.filter(id=booking_user_id).select_related('account')), None)
        if booking_user is None:
            return self.request.user
        return booking_user

    @cached_property
    def booking_userprofile(self):
        """
        Returns the userprofile the reservation is actually for.
        Corp accts can allow users to book on behalf of others, companions might not have users so need to use UP.
        Defaults to currently logged in userprofile if no booking user profile set.
        Returns:

        """
        booking_userprofile_id = self.request.session.get('booking_userprofile_id')
        if booking_userprofile_id is None:
            return self.request.user.userprofile

        booking_userprofile = next(iter(UserProfile.objects.filter(id=booking_userprofile_id).select_related('account')), None)
        if booking_userprofile is None:
            return self.request.user.userprofile
        return booking_userprofile

    def set_booking_user(self, booking_user):
        """
        Set the booking user.
        """
        self.booking_user = booking_user
        if booking_user is None:
            self.clear_booking_user()
        else:
            self.request.session['booking_user_id'] = booking_user.id

    def set_booking_userprofile(self, booking_userprofile):
        """
        Set the booking user.
        """
        self.booking_userprofile = booking_userprofile
        if booking_userprofile is None:
            self.clear_booking_userprofile()
        else:
            self.request.session['booking_userprofile_id'] = booking_userprofile.id

    def clear_booking_user(self):
        """
        Clears the booking user from the session
        """
        if 'booking_user_id' in self.request.session:
            del self.request.session['booking_user_id']

    def clear_booking_userprofile(self):
        """
        Clears the booking user from the session
        """
        if 'booking_userprofile_id' in self.request.session:
            del self.request.session['booking_userprofile_id']

class ReservationMixin(BaseReservationMixin):
    """
    Mixin which provides access to the reservation object in a request session as well as auto-renews on request
    """

    def dispatch(self, request, *args, **kwargs):
        """
        if auto renew is on, renew on any request

        if reservation is required, redirect if None
        """
        if self.require_permissions:
            user = self.booking_user or request.user

            # AMF RISE-356 check for active restriction window.
            if user.user_profile:
                restriction = user.user_profile.active_noshow_restriction()
                if restriction:
                    if self.booking_user != self.request.user: # this reservation is on behalf of another.  Although the msg key
                        # says "Admin" technically this message would be used anytime someone else books on behalf of the restricted person.
                        # be it an admin or a corporate or individual member.
                        msg = AutomatedMessage.objects.filter(message_key=AutomatedMessage.NO_SHOW_RESTRICTION_ADMIN).first()
                        if msg:
                            msg_txt = msg.message_box_text.replace("[[end_date]]", restriction.end_date.strftime("%m-%d-%Y"))
                            msg_txt = msg_txt.replace("[[FAQ_link]]", ("<a href='%s/faq' target='_blank'>here</a>" % settings.WP_URL))
                            messages.error(self.request, msg_txt)
                        else:
                            messages.error(self.request, "This person is restricted from all RISE activity until %s due to excessive no-shows." % restriction.end_date)

                    else:
                        msg = AutomatedMessage.objects.filter(message_key=AutomatedMessage.NO_SHOW_RESTRICTION_MEMBER).first()
                        if msg:
                            msg_txt = msg.message_box_text.replace("[[end_date]]", restriction.end_date.strftime("%m-%d-%Y"))
                            msg_txt = msg_txt.replace("[[FAQ_link]]", ("<a href='%s/faq' target='_blank'>here</a>" % settings.WP_URL))
                            messages.error(self.request, msg_txt)
                        else:
                            messages.error(self.request, "You are restricted from all RISE activity until %s due to excessive no-shows." % restriction.end_date)

                    return redirect('dashboard')

            if not user.has_perm('accounts.can_fly'):
                if not user.has_perm('accounts.can_book_team'):
                    messages.error(request, 'You do not have permission to book a flight.<br/><br/> Please contact 844-359-7473 or <a href="mailto:support@iflyrise.com">support@iflyrise.com.</a>')
                    return redirect('dashboard')

                return redirect('book_team_member')

            #AMF fix bug where admin users w/o accounts get a hard error here
            if user.account is None or not user.account.status == Account.STATUS_ACTIVE:
                messages.error(request, 'You do not have permission to book a flight.<br/><br/> Please contact 844-359-7473 or <a href="mailto:support@iflyrise.com">support@iflyrise.com.</a>')
                return redirect('dashboard')

        if self.reservation_required:
            if self.reservation is None:
                if self.redirect_name is not None:
                    return redirect(self.redirect_name)
                raise Http404

        if self.auto_renew and self.reservation is not None:
            self.reservation.renew()

        return super(ReservationMixin, self).dispatch(request, *args, **kwargs)


class CancellationMixin(BaseReservationMixin):
    """
    Mixin which provides access to the reservation object in a request session for the purpose of canceling
    """

    def dispatch(self, request, *args, **kwargs):
        """
        if reservation is required, redirect if None
        """

        if self.require_permissions:
            user = self.booking_user or request.user

            if not user.has_perm('accounts.can_fly'):
                if not user.has_perm('accounts.can_book_team'):
                    messages.error(request, 'You do not have permission to cancel a flight.<br/><br/> Please contact 844-359-7473 or <a href="mailto:support@iflyrise.com">support@iflyrise.com.</a>')
                    return redirect('dashboard')

            if not user.account.status == Account.STATUS_ACTIVE:
                messages.error(request, 'You do not have permission to cancel a flight.<br/><br/> Please contact 844-359-7473 or <a href="mailto:support@iflyrise.com">support@iflyrise.com.</a>')
                return redirect('dashboard')

        if self.reservation_required:
            if self.reservation is None:
                if self.redirect_name is not None:
                    return redirect(self.redirect_name)
                raise Http404

        return super(CancellationMixin, self).dispatch(request, *args, **kwargs)
