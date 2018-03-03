from django.conf import settings
from django.views.generic import View, DetailView, FormView, UpdateView, TemplateView, ListView, CreateView, DeleteView, WeekArchiveView, MonthArchiveView
from django.views.generic.detail import SingleObjectMixin
from django.views.generic.edit import FormMixin
from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from django.core.urlresolvers import reverse, reverse_lazy
from django.http import Http404, HttpResponseRedirect
from django.utils import timezone
from django.utils.functional import cached_property
from django.http import HttpResponse
from django.db import models, transaction

import arrow
from datetime import datetime
import json
from accounts.mixins import StaffRequiredMixin, PermissionRequiredMixin
from accounts.models import User
from .admin_forms import AnnouncementForm,AnnouncementListForm
from .models import Announcement,AutomatedMessage


class AdminAnnouncementListView(StaffRequiredMixin, PermissionRequiredMixin, FormView):
    """
    Admin View to display a list of announcements
    """
    permission_required = 'accounts.can_manage_announcements'
    model = AutomatedMessage
    template_name = 'announcements/admin/announcement_list.html'
    form_class = AnnouncementListForm

    def get_context_data(self, **kwargs):
        context = super(AdminAnnouncementListView, self).get_context_data(**kwargs)
        context.update({
            'announcement_list': Announcement.objects.all(),

        })

        return context

    def form_valid(self, form):
        message_key = form.cleaned_data.get('message_key')
        sms_text = form.cleaned_data.get('sms_text')
        email_text = form.cleaned_data.get('email_text')
        message_box_text = form.cleaned_data.get('message_box_text')
        if sms_text is not None or email_text is not None:
            automated_message = AutomatedMessage.objects.filter(message_key=message_key).first()
            if automated_message is None:  # this should not happen!
                automated_message = AutomatedMessage()
            if sms_text is not None and len(sms_text) > 0:
                automated_message.sms_text = sms_text
            if email_text is not None and len(email_text) > 0:
                automated_message.email_text = email_text
            if message_box_text is not None and len(message_box_text) > 0:
                automated_message.message_box_text = message_box_text
            automated_message.message_key = message_key
            automated_message.save()
        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse('admin_announcements_list')


class AdminAnnouncementDetailView(StaffRequiredMixin, PermissionRequiredMixin, DetailView):
    """
    Admin view to show announcement details
    """

    permission_required = 'accounts.can_manage_announcements'
    model = Announcement
    template_name = 'announcements/admin/announcement_detail.html'
    context_object_name = 'announcement'


class AdminAnnouncementCreateView(StaffRequiredMixin, PermissionRequiredMixin, CreateView):
    """
    Admin view to add a :class:`announcements.models.Announcement`
    """

    permission_required = 'accounts.can_manage_announcements'
    template_name = 'announcements/admin/announcement_form.html'
    form_class = AnnouncementForm
    model = Announcement
    context_object_name = 'announcement'

    def dispatch(self, request, *args, **kwargs):
        if Announcement.objects.all().count() >= 3:
            messages.error(self.request, 'Sorry, there are more than three Rise system announcements. Please delete an existing announcement before adding a new one.')
            return redirect('admin_announcements_list')
        else:
            return super(AdminAnnouncementCreateView, self).dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        response = super(AdminAnnouncementCreateView, self).form_valid(form)
        announcement = form.save(commit=False)
        announcement.created_by = self.request.user
        announcement.save()

        return response

    def get_success_url(self):
        return reverse('admin_announcements_detail', args=(self.object.id,))


class AdminAnnouncementUpdateView(StaffRequiredMixin, PermissionRequiredMixin, UpdateView):
    """
    Admin view to update an announcement
    """

    permission_required = 'accounts.can_manage_announcements'
    model = Announcement
    template_name = 'announcements/admin/announcement_form.html'
    form_class = AnnouncementForm
    context_object_name = 'announcement'

    def get_success_url(self):
        return reverse('admin_announcements_detail', args=(self.object.id,))


class AdminAnnouncementDeleteView(StaffRequiredMixin, PermissionRequiredMixin, DeleteView):
    """
    Admn view to delete an announcement
    """
    permission_required = 'accounts.can_manage_announcements'
    template_name = 'announcements/admin/announcement_confirm_delete.html'
    model = Announcement
    context_object_name = 'announcement'
    success_url = reverse_lazy('admin_announcements_list')


class MessageChoicesView(View):
    def get(self, request, *args, **kwargs):
        message_key = request.GET.get('key')
        automated_message = AutomatedMessage.objects.filter(message_key=message_key).first()
        if automated_message is not None:
            json_result = json.dumps({"sms_text":automated_message.sms_text,"email_text":automated_message.email_text, "message_box_text": automated_message.message_box_text, "substitution_info": automated_message.substitution_info})
        else:
            json_result = json.dumps({})
        return HttpResponse(json_result, content_type='application/json')
