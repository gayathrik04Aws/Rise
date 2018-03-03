from django.views.generic import FormView
from django.contrib import messages
from django.core.urlresolvers import reverse_lazy

from .models import Flight
from accounts.mixins import LoginRequiredMixin
from .forms import FlightFeedbackForm


class FlightFeedbackView(LoginRequiredMixin, FormView):
    """
    Add Flight Feedback
    """
    template_name = 'flights/flight_feedback.html'
    form_class = FlightFeedbackForm

    def get_form_kwargs(self):
        kwargs = super(FlightFeedbackView, self).get_form_kwargs()

        kwargs.update({
            'user': self.request.user,
        })

        return kwargs

    def get_success_url(self):
        return reverse_lazy('flight', kwargs=self.kwargs)

    def form_valid(self, form):
        response = super(FlightFeedbackView, self).form_valid(form)

        flight_pk = self.kwargs.get('pk', None)

        self.object = form.save()
        self.object.user = form.user
        self.object.flight = next(iter(Flight.objects.filter(id=flight_pk)))
        self.object.save()

        messages.info(self.request, 'Your feedback has been sent!')
        return response
