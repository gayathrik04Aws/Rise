from django.contrib import admin

from import_export import resources, widgets, fields
from import_export.admin import ImportExportMixin

from .models import (
    Airport, Plane, Route, RouteTime, RouteTimePlanRestriction, Flight, FlightPlanRestriction, FlightFeedback,
    FlightMessage, RouteTimePlanSeatRestriction, FlightPlanSeatRestriction
)


class AirportResource(resources.ModelResource):
    class Meta:
        model = Airport

class AirportAdmin(ImportExportMixin, admin.ModelAdmin):
    resource_class = AirportResource
    pass

admin.site.register(Airport, AirportAdmin)


class PlaneAdmin(admin.ModelAdmin):
    pass

admin.site.register(Plane, PlaneAdmin)


class RouteAdmin(admin.ModelAdmin):
    pass

admin.site.register(Route, RouteAdmin)


class RouteTimeAdmin(admin.ModelAdmin):
    pass

admin.site.register(RouteTime, RouteTimeAdmin)


class RouteTimePlanRestrictionAdmin(admin.ModelAdmin):
    pass

admin.site.register(RouteTimePlanRestriction, RouteTimePlanRestrictionAdmin)


class RouteTimePlanSeatRestrictionAdmin(admin.ModelAdmin):
    pass

admin.site.register(RouteTimePlanSeatRestriction, RouteTimePlanSeatRestrictionAdmin)


class FlightAdmin(admin.ModelAdmin):
    pass

admin.site.register(Flight, FlightAdmin)


class FlightPlanRestrictionAdmin(admin.ModelAdmin):
    pass

admin.site.register(FlightPlanRestriction, FlightPlanRestrictionAdmin)


class FlightPlanSeatRestrictionAdmin(admin.ModelAdmin):
    pass

admin.site.register(FlightPlanSeatRestriction, FlightPlanSeatRestrictionAdmin)


class FlightFeedbackAdmin(admin.ModelAdmin):
    pass

admin.site.register(FlightFeedback, FlightFeedbackAdmin)


class FlightMessageAdmin(admin.ModelAdmin):
    list_display = ('flight', 'message', 'created', 'created_by')

admin.site.register(FlightMessage, FlightMessageAdmin)
