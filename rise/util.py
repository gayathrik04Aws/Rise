import datetime

from django.http.response import Http404
from django.views.generic import ListView, FormView
from django.views.generic.edit import FormMixin, BaseFormView


def duration_as_time(minutes):
    hours = int(minutes/60)
    minutes %= 60

    return datetime.time(hours, minutes)


class FormListView(FormMixin, ListView):
    object_list = None
    
    def get_context_data(self, **kwargs):
        kwargs.update({
            'form': self.get_form(),
        })
        return super(FormListView, self).get_context_data(**kwargs)

    def get(self, request, *args, **kwargs):
        self.object_list = self.get_queryset()
        return super(FormListView, self).get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)
