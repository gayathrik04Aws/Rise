from django.contrib import admin

from import_export import resources, widgets, fields
from import_export.admin import ImportExportMixin

from anywhere.models import AnywhereRoute, AnywhereFlightRequest, AnywhereFlightSet
from flights.admin import RouteAdmin
from flights.models import Airport


class AnywhereRouteResource(resources.ModelResource):
    class Meta:
        model = AnywhereRoute
        widgets = {
            'origin': {'field': 'code'},
            'destination': {'field': 'code'}
        }


class AnywhereRouteAdmin(ImportExportMixin, RouteAdmin):
    resource_class = AnywhereRouteResource

admin.site.register(AnywhereRoute, AnywhereRouteAdmin)
admin.site.register(AnywhereFlightRequest, admin.ModelAdmin)


class AnywhereFlightSetAdmin(admin.ModelAdmin):
    list_display = ('pk', 'public_key', 'created_by', 'sharing', 'confirmation_status', )
    list_display_links = ('pk', 'public_key', )



admin.site.register(AnywhereFlightSet, AnywhereFlightSetAdmin)
