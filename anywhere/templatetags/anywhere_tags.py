import datetime

from django import template

register = template.Library()


@register.simple_tag(takes_context=True)
def anywhere_request_count(context, req_type):
    # temporarily cache results in template context - this tag tends to be present multiple times on one page
    try:
        counts = context['_afr_counts']
    except KeyError:
        from anywhere.admin_views import (
            AdminAnywherePendingRequestList, AdminAnywhereReadyRequestList, AdminAnywhereUnconfirmedRequestList, AdminAnywhereConfirmedRequestList
        )

        counts = context['_afr_counts'] = {
            'pending': AdminAnywherePendingRequestList.queryset.count(),
            'ready': AdminAnywhereReadyRequestList.queryset.count(),
            'unconfirmed': AdminAnywhereUnconfirmedRequestList.queryset.count(),
            'confirmed': AdminAnywhereConfirmedRequestList.queryset.count()
        }

    return counts.get(req_type, '0')
