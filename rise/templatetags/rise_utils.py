from django import template
from django.contrib.auth.models import Group
from django.template import defaultfilters

register = template.Library()


@register.filter(name='has_group')
def has_group(user, group_name):
    try:
        group = Group.objects.get(name=group_name)
    except:
        return False  # group doesn't exist, so for sure the user isn't part of the group

    # for superuser or staff, always return True
    if user.is_superuser or user.is_staff:
        return True

    return user.groups.filter(name=group_name).exists()


@register.filter(name='pickadate_data')
def pickadate_data(date_field, fmt="Y-m-d"):
    """
    Supplement a date form field with the data-value attribute so pickadate.js properly re-parses stored data.
    """
    if date_field.data is not None:  # pass submitFormat back to data-value
        date_field.field.widget.attrs['data-value'] = date_field.data
    else:
        val = date_field.value()

        if val is not None:
            date_field.field.widget.attrs['data-value'] = defaultfilters.date(val, fmt)

    return date_field
