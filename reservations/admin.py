from django.contrib import admin

from .models import Reservation, FlightReservation, Passenger, FlightWaitlist, FlightPassengerAuditTrail


class PassengerInline(admin.TabularInline):
    model = Passenger


class ReservationAdmin(admin.ModelAdmin):
    pass

admin.site.register(Reservation, ReservationAdmin)


class FlightReservationAdmin(admin.ModelAdmin):
    list_display = ('flight', 'status',)
    inlines = (PassengerInline,)
    list_filter = ('status',)
    readonly_fields = ('created',)

admin.site.register(FlightReservation, FlightReservationAdmin)


class PassengerAdmin(admin.ModelAdmin):
    pass

admin.site.register(Passenger, PassengerAdmin)


class FlightWaitlistAdmin(admin.ModelAdmin):
    pass

admin.site.register(FlightWaitlist, FlightWaitlistAdmin)


class FlightPassengerAuditTrailAdmin(admin.ModelAdmin):
    pass

admin.site.register(FlightPassengerAuditTrail, FlightPassengerAuditTrailAdmin)
