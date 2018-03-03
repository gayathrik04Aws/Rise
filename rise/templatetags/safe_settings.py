from django import template
from django.conf import settings

register = template.Library()


@register.simple_tag
def settings_value(name):
    # restrict retrieval of settings values to an explicit safe_list
    safe_list = ['PASS_COST', 'COMPANION_PASS_COST', 'DEPOSIT_COST', 'DEPOSIT_TAX_PERCENT', 'FET_TAX',
                 'DEPOSIT_TAX_PERCENT', 'COMPANION_PASS_COST_ROUND_TRIP','CLOUDSPONGE_KEY','FACEBOOK_SHARE_LINK_TITLE', 'LOAD_AVATARS']
    if name in safe_list:
        return getattr(settings, name, "")
    else:
        return None
