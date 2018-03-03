from django import template
from copy import copy

from datetime import timedelta, time

register = template.Library()


@register.filter(name='human_duration')
def human_duration(value):
    """
    Returns the humanized duration with the given minutes
    """
    if value is None or value == "":
        return ''

    hours = value / 60
    minutes = value % 60

    human = ''

    if hours > 0:
        human = '%d HR' % hours

    if minutes > 0:
        if len(human) > 0:
            human += ' + '
        human += '%d MIN' % minutes

    return human


@register.filter
def simple_duration(value):
    """
    Returns the humanized duration with the given minutes
    """
    if value is None:
        return None

    if type(value) is unicode:
        return value

    mins = value
    if type(value) is timedelta:
        mins = value.seconds / 60

    if type(value) is time:
        return '%d:%02d' % (value.hour, value.minute)

    hours = mins / 60
    minutes = mins % 60

    return '%d:%02d' % (hours, minutes)


@register.filter
def in_list(value, arg):
    """
    Returns True if value is in arg

    For checking if a value is in a list given as the arg in a template
    """
    return value in arg


@register.filter
def route_time_days(route_time):
    output = ''
    if route_time.sunday:
        output += 'Su '
    if route_time.monday:
        output += 'M '
    if route_time.tuesday:
        output += 'Tu '
    if route_time.wednesday:
        output += 'W '
    if route_time.thursday:
        output += 'Th '
    if route_time.friday:
        output += 'F '
    if route_time.saturday:
        output += 'Sa '

    return output.strip()

@register.filter
def week_number_of_year(date_time):
    return date_time.strftime("%U")

@register.filter(is_safe=True)
def remove_spaces_lower_case(value):
    return value.replace(" ","").lower()

@register.filter
def instances_and_widgets(bound_field):
    """Returns a list of two-tuples of instances and widgets, designed to
    be used with ModelMultipleChoiceField and CheckboxSelectMultiple widgets.

    Allows templates to loop over a multiple checkbox field and display the
    related model instance, such as for a table with checkboxes.

    Usage:
       {% for instance, widget in form.my_field_name|instances_and_widgets %}
           <p>{{ instance }}: {{ widget }}</p>
       {% endfor %}
    """
    instance_widgets = []
    index = 0
    for instance in bound_field.field.queryset.all():
         widget = copy(bound_field[index])
         # Hide the choice label so it just renders as a checkbox
         widget.choice_label = ''
         instance_widgets.append((instance, widget))
         index += 1
    return instance_widgets

@register.filter
def sub_seats(seats_available,total_seats):
    return total_seats - seats_available

@register.filter
def load_factor(seats_available,total_seats):
    if total_seats <= 0:
        return 0
    seats_filled = total_seats-seats_available
    load_factor = float(seats_filled) / float(total_seats)
    return long(load_factor*100)

@register.filter
def get_value(waitlistdict,id):
    if waitlistdict.get(id) is not None:
        return waitlistdict.get(id)
    else:
        return ""
