from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Q
import json

from .forms import AnnouncementForm, ScheduledEmailReportForm
from .models import RecipientGroup, Announcement, ScheduledEmailReport
from accounts.models import User
from .tasks import send_review_report

def author_required(view_func):
    def _wrapped_view(request, *args, **kwargs):
        allowed_roles = [User.SUPERADMIN, User.CORPORATE, User.RISORSE_UMANE]
        if not request.user.is_authenticated or request.user.role not in allowed_roles:
            messages.error(request, "Non hai i permessi per accedere a questa pagina.")
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

@login_required
@author_required
def create_announcement(request):
    if request.method == 'POST':
        form = AnnouncementForm(request.POST)
        form.fields['load_group'].queryset = RecipientGroup.objects.filter(owner=request.user)

        if form.is_valid():
            # --- Handle saving a new group ---
            if form.cleaned_data.get('save_group'):
                new_group_name = form.cleaned_data.get('new_group_name')
                if new_group_name:
                    new_group = RecipientGroup.objects.create(
                        name=new_group_name,
                        owner=request.user,
                        roles=",".join(form.cleaned_data.get('target_roles', []))
                    )
                    new_group.resorts.set(form.cleaned_data.get('target_resorts', []))
                    new_group.users.set(form.cleaned_data.get('recipients', []))
                    messages.info(request, f"Gruppo '{new_group_name}' salvato per uso futuro.")
                else:
                    messages.warning(request, "Per salvare un gruppo, devi fornirgli un nome.")

            # --- Handle sending the announcement ---
            announcement = form.save(commit=False)
            announcement.author = request.user
            announcement.save()

            target_resorts = form.cleaned_data.get('target_resorts')
            target_roles = form.cleaned_data.get('target_roles')
            specific_recipients = form.cleaned_data.get('recipients')

            final_recipients = set(specific_recipients)

            if target_resorts or target_roles:
                user_query = Q()
                if target_resorts:
                    user_query &= Q(resort__in=target_resorts)
                if target_roles:
                    user_query &= Q(role__in=target_roles)

                users_from_query = User.objects.filter(user_query).distinct()
                final_recipients.update(users_from_query)

            announcement.recipients.set(final_recipients)

            messages.success(request, f"Annuncio inviato con successo a {len(final_recipients)} utente/i.")
            return redirect('communications:create')
    else:
        form = AnnouncementForm()
        form.fields['load_group'].queryset = RecipientGroup.objects.filter(owner=request.user)

    # Prepare data for JS
    groups = RecipientGroup.objects.filter(owner=request.user).prefetch_related('users', 'resorts')
    groups_data = [
        {
            'id': group.id,
            'name': group.name,
            'users': list(group.users.values_list('id', flat=True)),
            'resorts': list(group.resorts.values_list('id', flat=True)),
            'roles': group.roles.split(',') if group.roles else []
        } for group in groups
    ]

    return render(request, 'communications/create_announcement.html', {
        'form': form,
        'groups_data': groups_data
    })

@login_required
@author_required
def announcement_update(request, pk):
    announcement = get_object_or_404(Announcement, pk=pk)
    # Ensure only the author or a superuser can edit
    if not (request.user == announcement.author or request.user.is_superuser):
        messages.error(request, "Non hai il permesso di modificare questo annuncio.")
        return redirect('profile')

    if request.method == 'POST':
        # We don't handle group logic on update, just content/recipients
        form = AnnouncementForm(request.POST, instance=announcement)
        if form.is_valid():
            # Same logic as create for calculating recipients
            updated_announcement = form.save(commit=False)

            target_resorts = form.cleaned_data.get('target_resorts')
            target_roles = form.cleaned_data.get('target_roles')
            specific_recipients = form.cleaned_data.get('recipients')
            final_recipients = set(specific_recipients)
            if target_resorts or target_roles:
                user_query = Q()
                if target_resorts:
                    user_query &= Q(resort__in=target_resorts)
                if target_roles:
                    user_query &= Q(role__in=target_roles)
                users_from_query = User.objects.filter(user_query).distinct()
                final_recipients.update(users_from_query)

            updated_announcement.save()
            updated_announcement.recipients.set(final_recipients)

            messages.success(request, "Annuncio aggiornato con successo.")
            return redirect('profile')
    else:
        # Pre-populate form with existing data
        # Note: this doesn't reverse the recipient calculation, it just shows the final list.
        # A more advanced implementation would be needed to re-populate the resort/role fields.
        form = AnnouncementForm(instance=announcement)

    # We can reuse the creation template
    return render(request, 'communications/create_announcement.html', {'form': form})


@login_required
@author_required
def announcement_delete(request, pk):
    announcement = get_object_or_404(Announcement, pk=pk)
    if not (request.user == announcement.author or request.user.is_superuser):
        messages.error(request, "Non hai il permesso di eliminare questo annuncio.")
        return redirect('profile')

    if request.method == 'POST':
        announcement.delete()
        messages.success(request, "Annuncio eliminato con successo.")
        return redirect('profile')

    return render(request, 'communications/announcement_confirm_delete.html', {'announcement': announcement})

@login_required
def announcement_detail(request, pk):
    announcement = get_object_or_404(Announcement, pk=pk)

    # User must be a recipient to view it
    if request.user not in announcement.recipients.all():
        messages.error(request, "Non sei un destinatario di questo annuncio.")
        return redirect('profile')

    # Mark as read
    announcement.read_by.add(request.user)

    return render(request, 'communications/announcement_detail.html', {'announcement': announcement})

@login_required
@author_required
def announcement_report(request, pk):
    announcement = get_object_or_404(Announcement.objects.prefetch_related('recipients', 'read_by'), pk=pk)

    # Only author or superuser can see the report
    if not (request.user == announcement.author or request.user.is_superuser):
        messages.error(request, "Non hai il permesso di visualizzare questo report.")
        return redirect('profile')

    all_recipients = announcement.recipients.all()
    read_recipients = announcement.read_by.all()
    unread_recipients = all_recipients.exclude(pk__in=read_recipients.values_list('pk', flat=True))

    context = {
        'announcement': announcement,
        'read_recipients': read_recipients,
        'unread_recipients': unread_recipients,
    }
    return render(request, 'communications/announcement_report.html', context)


# --- Scheduled Email Report Views ---
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import UserPassesTestMixin
from .models import ScheduledEmailReport
from .forms import ScheduledEmailReportForm
from .tasks import send_review_report

class SuperuserRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_superuser

class ScheduledEmailReportListView(SuperuserRequiredMixin, ListView):
    model = ScheduledEmailReport
    template_name = 'communications/scheduled_report_list.html'
    context_object_name = 'reports'

class ScheduledEmailReportCreateView(SuperuserRequiredMixin, CreateView):
    model = ScheduledEmailReport
    form_class = ScheduledEmailReportForm
    template_name = 'communications/scheduled_report_form.html'
    success_url = reverse_lazy('communications:scheduled_report_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Crea Nuovo Report Programmato'
        return context

class ScheduledEmailReportUpdateView(SuperuserRequiredMixin, UpdateView):
    model = ScheduledEmailReport
    form_class = ScheduledEmailReportForm
    template_name = 'communications/scheduled_report_form.html'
    success_url = reverse_lazy('communications:scheduled_report_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Modifica Report: {self.object.name}'
        return context

class ScheduledEmailReportDeleteView(SuperuserRequiredMixin, DeleteView):
    model = ScheduledEmailReport
    template_name = 'communications/scheduled_report_confirm_delete.html'
    success_url = reverse_lazy('communications:scheduled_report_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f"Elimina Report: {self.object.name}"
        return context

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.object.periodic_task:
            self.object.periodic_task.delete()
        messages.success(self.request, f"Report programmato '{self.object.name}' eliminato con successo.")
        return super().delete(request, *args, **kwargs)

@login_required
@user_passes_test(lambda u: u.is_superuser)
def send_instant_report_view(request, pk):
    report = get_object_or_404(ScheduledEmailReport, pk=pk)
    if request.method == 'POST':
        start_date_str = request.POST.get('start_date')
        end_date_str = request.POST.get('end_date')

        # Basic validation
        if not start_date_str or not end_date_str:
            messages.error(request, "Per un invio personalizzato, entrambe le date sono richieste.")
            return redirect('communications:scheduled_report_list')

        # Trigger the task with the specified date range
        send_review_report.delay(report.id, start_date_str=start_date_str, end_date_str=end_date_str)
        messages.success(request, f"L'invio personalizzato del report '{report.name}' è stato avviato.")
        return redirect('communications:scheduled_report_list')

    # For a GET request, just trigger with the default (last day)
    # This can be used for a simple "send yesterday's report now" button
    send_review_report.delay(report.id)
    messages.success(request, f"L'invio del report per il giorno precedente '{report.name}' è stato avviato.")
    return redirect('communications:scheduled_report_list')
