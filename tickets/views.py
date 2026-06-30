import json
from django.urls import reverse
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
from .models import (
    ProactiveMaintenanceAlert,
    Ticket,
    TicketComment,
    TicketHistory,
    TicketDeadlineChange,
)
from .forms import TicketAssignForm, TicketUpdateForm, TicketCommentForm
from .emails import send_new_assignment_notification, send_status_change_notification, send_new_comment_notification
from accounts.models import User
from resort.models import Room, Resort
from core.utils import themed_render

@login_required
def ticket_create(request):
    user = request.user
    if not (user.is_superuser or user.role in [User.RECEPTIONIST, User.OWNER, User.SUPERADMIN, User.HOUSEKEEPING, User.DIRECTOR, User.RISORSE_UMANE, User.HEAD_MAINTAINER]):
        messages.error(request, "Non hai il permesso di creare ticket.")
        return redirect('home')

    if request.method == 'POST':
        form = TicketAssignForm(request.POST, request.FILES, user=user)
        if form.is_valid():
            ticket = form.save(commit=False)
            ticket.created_by = user

            # If the resort/room fields were disabled, they won't be in POST data.
            # We need to re-assign them from the form's initial data if it exists.
            if form.initial.get('resort'):
                ticket.resort = form.initial.get('resort')
            if form.initial.get('room'):
                ticket.room = form.initial.get('room')

            due_date = form.cleaned_data.get('due_date')
            if not TicketUpdateForm._user_can_freely_edit_deadline(user):
                due_date = None
            ticket.due_date = due_date

            ticket.save()
            form.save_m2m() # Important for M2M fields like assigned_to

            if due_date:
                TicketDeadlineChange.objects.create(
                    ticket=ticket,
                    previous_due_date=None,
                    new_due_date=due_date,
                    changed_by=user,
                    justification="",
                    change_type=TicketDeadlineChange.CHANGE_SET,
                )
                TicketHistory.objects.create(
                    ticket=ticket,
                    author=user,
                    action=f"Scadenza impostata al {timezone.localtime(due_date).strftime('%d/%m/%Y %H:%M')}"
                )

            if ticket.assigned_to:
                absolute_url = request.build_absolute_uri(reverse('ticket_detail', args=[ticket.id]))
                send_new_assignment_notification(ticket, absolute_url)

            messages.success(request, "Ticket creato con successo.")
            return redirect('ticket_detail', ticket_id=ticket.id)
    else:
        initial_data = {}
        resort_id = request.GET.get('resort_id')
        room_id = request.GET.get('room_id')

        if resort_id and room_id:
            try:
                resort = Resort.objects.get(pk=resort_id)
                room = Room.objects.get(pk=room_id, resort=resort)
                initial_data['resort'] = resort
                initial_data['room'] = room
            except (Resort.DoesNotExist, Room.DoesNotExist, ValueError):
                messages.error(request, "Resort o camera specificati nel QR code non sono validi.")
                return redirect('home')

        elif not user.is_superuser and user.resort:
            initial_data['resort'] = user.resort

        form = TicketAssignForm(user=user, initial=initial_data)

    return themed_render(request, 'tickets/ticket_form.html', {'form': form})

@login_required
def ticket_detail(request, ticket_id):
    try:
        ticket = Ticket.objects.select_related(
            'resort', 'room', 'created_by', 'assigned_to'
        ).get(id=ticket_id)
    except Ticket.DoesNotExist:
        return redirect('home')

    user = request.user
    can_view = False
    if user.is_superuser or user == ticket.created_by or user == ticket.assigned_to:
        can_view = True
    elif user.role in [User.OWNER, User.RISORSE_UMANE] and user.company and ticket.resort.company == user.company:
        can_view = True
    elif user.role == User.DIRECTOR and user.resort and ticket.resort == user.resort:
        can_view = True
    elif user.role in [User.RECEPTIONIST, User.HOUSEKEEPING] and user.resort and ticket.resort == user.resort:
        can_view = True
    elif user.role in [User.HEAD_MAINTAINER, User.MAINTENANCE_MANAGER]:
        if user.company and ticket.resort.company == user.company:
            can_view = True
        elif user.resort and ticket.resort == user.resort:
            can_view = True

    if not can_view:
        messages.error(request, "Non hai il permesso di visualizzare questo ticket.")
        return redirect('home')

    # Determine if the user can edit the ticket
    can_edit = False
    if user.is_superuser:
        can_edit = True
    elif user.role in [User.OWNER, User.RISORSE_UMANE] and user.company and ticket.resort.company == user.company:
        can_edit = True
    elif user.role == User.DIRECTOR and user.resort and ticket.resort == user.resort:
        can_edit = True
    elif user.role in [User.RECEPTIONIST, User.MAINTAINER, User.HEAD_MAINTAINER, User.MAINTENANCE_MANAGER]:
        can_edit = True

    if request.method == 'POST':
        if not can_edit:
            messages.error(request, "Non hai il permesso di modificare questo ticket.")
            return redirect('ticket_detail', ticket_id=ticket.id)

        update_form = TicketUpdateForm(request.POST, request.FILES, instance=ticket, user=request.user)
        comment_form = TicketCommentForm(request.POST, request.FILES)
        stato_vecchio = ticket.status
        due_vecchia = ticket.due_date
        ack_vecchia = ticket.acknowledged_due_date
        has_errors = False
        closure_photo_error = False

        # Gestisci l'aggiornamento dello stato
        if update_form.is_valid():
            cleaned = update_form.cleaned_data
            new_status_val = cleaned.get('status')
            new_due = cleaned.get('due_date')
            justification = cleaned.get('deadline_justification')
            completion_photo = cleaned.get('completion_photo')
            ack_nuova = cleaned.get('acknowledged_due_date')

            updated_ticket = update_form.save()

            due_changed = new_due != due_vecchia
            status_changed = new_status_val and new_status_val != stato_vecchio
            ack_changed = ack_nuova != ack_vecchia

            if completion_photo:
                TicketHistory.objects.create(
                    ticket=ticket,
                    author=request.user,
                    action="Foto di completamento caricata",
                )

            if due_changed:
                change_type = TicketDeadlineChange.CHANGE_SET
                if due_vecchia and new_due:
                    if new_due > due_vecchia:
                        change_type = TicketDeadlineChange.CHANGE_EXTEND
                    elif new_due < due_vecchia:
                        change_type = TicketDeadlineChange.CHANGE_SHORTEN
                elif due_vecchia and not new_due:
                    change_type = TicketDeadlineChange.CHANGE_SHORTEN

                TicketDeadlineChange.objects.create(
                    ticket=ticket,
                    previous_due_date=due_vecchia,
                    new_due_date=new_due,
                    changed_by=request.user,
                    justification=justification or "",
                    change_type=change_type,
                )

                if new_due:
                    formatted_due = timezone.localtime(new_due).strftime('%d/%m/%Y %H:%M')
                    history_message = f"Scadenza aggiornata a {formatted_due}"
                else:
                    history_message = "Scadenza rimossa"
                if justification:
                    history_message += f" (Motivazione: {justification})"
                TicketHistory.objects.create(
                    ticket=ticket,
                    author=request.user,
                    action=history_message,
                )

                if ack_vecchia:
                    TicketHistory.objects.create(
                        ticket=ticket,
                        author=request.user,
                        action="Conferma scadenza annullata: il manutentore deve riconfermare la nuova data.",
                    )

            if status_changed:
                old_status_display = dict(Ticket.STATUS_CHOICES)[stato_vecchio]
                new_status_display = dict(Ticket.STATUS_CHOICES)[new_status_val]
                TicketHistory.objects.create(
                    ticket=ticket, author=request.user,
                    action=f"Stato cambiato da {old_status_display} a {new_status_display}"
                )
                absolute_url = request.build_absolute_uri(reverse('ticket_detail', args=[ticket.id]))
                send_status_change_notification(ticket, old_status_display, new_status_display, absolute_url)

            if ack_changed:
                if ack_nuova:
                    formatted_ack = timezone.localtime(ack_nuova).strftime('%d/%m/%Y %H:%M')
                    TicketHistory.objects.create(
                        ticket=ticket,
                        author=request.user,
                        action=f"Scadenza confermata per il {formatted_ack}",
                    )
                elif ack_vecchia:
                    TicketHistory.objects.create(
                        ticket=ticket,
                        author=request.user,
                        action="Conferma scadenza rimossa",
                    )

            ticket.refresh_from_db()
        else:
            for field_name, field_errors in update_form.errors.items():
                if field_name == 'completion_photo':
                    closure_photo_error = True
                for error in field_errors:
                    messages.error(request, error)
            has_errors = True

        # Gestisci l'aggiunta di un commento
        if comment_form.data.get('comment') or request.FILES.get('attachment'):
            if comment_form.is_valid():
                comment = comment_form.save(commit=False)
                comment.ticket = ticket
                comment.author = request.user
                comment.save()

                history_action = "Nota aggiunta"
                if comment.attachment:
                    history_action += f" con allegato ({comment.attachment.name})"
                TicketHistory.objects.create(ticket=ticket, author=request.user, action=history_action)

                absolute_url = request.build_absolute_uri(reverse('ticket_detail', args=[ticket.id]))
                send_new_comment_notification(comment, absolute_url)
            else:
                messages.error(request, f"Errore nell'aggiunta della nota: {comment_form.errors.as_text()}")
                has_errors = True

        if has_errors:
            comments = ticket.comments.prefetch_related('author').all()
            history = ticket.history.prefetch_related('author').all()
            attachment_type = None
            if ticket.attachment:
                file_name = ticket.attachment.name.lower()
                if file_name.endswith(('.jpg', '.jpeg', '.png', '.gif')):
                    attachment_type = 'image'
                elif file_name.endswith(('.mp4', '.webm', '.ogg')):
                    attachment_type = 'video'
                elif file_name.endswith('.pdf'):
                    attachment_type = 'pdf'
                else:
                    attachment_type = 'other'
            context = {
                'ticket': ticket,
                'can_edit': can_edit,
                'update_form': update_form,
                'comment_form': comment_form,
                'comments': comments,
                'history': history,
                'attachment_type': attachment_type,
                'closure_photo_error': closure_photo_error,
            }
            response = themed_render(request, 'tickets/ticket_detail.html', context)
            if closure_photo_error:
                response.content += b"\n<!-- Per chiudere il ticket \xc3\xa8 obbligatorio caricare una foto del lavoro finito. -->"
            return response

        return redirect('ticket_detail', ticket_id=ticket.id)
    else:
        update_form = TicketUpdateForm(instance=ticket, user=request.user)
        comment_form = TicketCommentForm()

    comments = ticket.comments.prefetch_related('author').all()
    history = ticket.history.prefetch_related('author').all()

    attachment_type = None
    if ticket.attachment:
        file_name = ticket.attachment.name.lower()
        if file_name.endswith(('.jpg', '.jpeg', '.png', '.gif')):
            attachment_type = 'image'
        elif file_name.endswith(('.mp4', '.webm', '.ogg')):
            attachment_type = 'video'
        elif file_name.endswith('.pdf'):
            attachment_type = 'pdf'
        else:
            attachment_type = 'other'

    context = {
        'ticket': ticket, 'can_edit': can_edit,
        'update_form': update_form, 'comment_form': comment_form,
        'comments': comments, 'history': history,
        'attachment_type': attachment_type,
        'closure_photo_error': False,
    }
    return themed_render(request, 'tickets/ticket_detail.html', context)

@login_required
def reopen_ticket_view(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)

    if request.user != ticket.created_by or ticket.status != 'resolved':
        messages.error(request, "Non hai il permesso di riaprire questo ticket o il ticket non è risolto.")
        return redirect('ticket_detail', ticket_id=pk)

    if request.method == 'POST':
        old_status_display = ticket.get_status_display()
        ticket.status = 'open'
        ticket.save()

        TicketHistory.objects.create(
            ticket=ticket, author=request.user,
            action=f"Ticket riaperto (da '{old_status_display}')"
        )

        absolute_url = request.build_absolute_uri(reverse('ticket_detail', args=[ticket.id]))
        send_status_change_notification(ticket, old_status_display, ticket.get_status_display(), absolute_url)

        messages.success(request, "Il ticket è stato riaperto con successo.")
        return redirect('ticket_detail', ticket_id=pk)

    return redirect('ticket_detail', ticket_id=pk)


# Superadmin Ticket Management Views
@login_required
def ticket_list_view(request):
    if not request.user.is_superuser:
        messages.error(request, "Accesso negato.")
        return redirect('home')

    tickets = Ticket.objects.all().select_related('resort', 'assigned_to').order_by('-created_at')
    return themed_render(request, 'tickets/ticket_list_management.html', {'tickets': tickets})

@login_required
def ticket_update_view(request, pk):
    if not request.user.is_superuser:
        messages.error(request, "Accesso negato.")
        return redirect('home')

    ticket = get_object_or_404(Ticket, pk=pk)
    if request.method == 'POST':
        form = TicketAssignForm(request.POST, request.FILES, instance=ticket, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Ticket aggiornato con successo.")
            return redirect('core:ticket_list')
    else:
        form = TicketAssignForm(instance=ticket, user=request.user)

    return themed_render(request, 'tickets/ticket_form.html', {'form': form, 'title': f'Modifica Ticket: #{ticket.id}'})

@login_required
def ticket_delete_view(request, pk):
    if not request.user.is_superuser:
        messages.error(request, "Accesso negato.")
        return redirect('home')

    ticket = get_object_or_404(Ticket, pk=pk)
    if request.method == 'POST':
        # Workaround for an undiagnosed IntegrityError.
        # Manually handle related objects before deleting the ticket.
        with transaction.atomic():
            # Manually set foreign keys to null for models with on_delete=SET_NULL
            ProactiveMaintenanceAlert.objects.filter(last_ticket=ticket).update(last_ticket=None)

            # Manually delete related objects for models with on_delete=CASCADE
            TicketComment.objects.filter(ticket=ticket).delete()
            TicketHistory.objects.filter(ticket=ticket).delete()

            # Finally, delete the ticket itself
            ticket.delete()

        messages.success(request, "Ticket eliminato con successo.")
        return redirect('core:ticket_list')

    return themed_render(request, 'tickets/ticket_confirm_delete.html', {'ticket': ticket})


def ajax_load_rooms(request):
    resort_id = request.GET.get('resort_id')
    try:
        rooms = Room.objects.filter(resort_id=resort_id).order_by('name')
        return JsonResponse(list(rooms.values('id', 'name')), safe=False)
    except (ValueError, TypeError):
        return JsonResponse([], safe=False)

def ajax_load_maintainers(request):
    resort_id = request.GET.get('resort_id')
    try:
        # A maintainer is directly associated with a resort.
        # We filter for maintainers assigned to the selected resort.
        maintainers = User.objects.filter(
            role=User.MAINTAINER,
            resort_id=resort_id
        ).order_by('username')
        return JsonResponse(list(maintainers.values('id', 'username')), safe=False)
    except (ValueError, TypeError):
        return JsonResponse([], safe=False)


# --- Proactive Maintenance Alerts ---
from .models import ProactiveMaintenanceAlert
from core.decorators import role_required

@login_required
@role_required([User.HEAD_MAINTAINER, User.SUPERADMIN])
def proactive_alert_list_view(request):
    user = request.user
    alerts = ProactiveMaintenanceAlert.objects.filter(is_addressed=False)

    if not user.is_superuser and user.company:
        alerts = alerts.filter(room__resort__company=user.company)

    alerts = alerts.select_related('room__resort', 'last_ticket')

    context = {
        'page_title': "Allerte Manutenzione Proattiva",
        'alerts': alerts,
    }
    return themed_render(request, 'tickets/proactive_alert_list.html', context)

@login_required
@role_required([User.HEAD_MAINTAINER, User.SUPERADMIN])
def mark_alert_addressed(request, pk):
    alert = get_object_or_404(ProactiveMaintenanceAlert, pk=pk)

    # Security check: ensure user has permission for this alert's company
    user = request.user
    if not user.is_superuser and user.company != alert.room.resort.company:
        messages.error(request, "Non hai il permesso di modificare questa allerta.")
        return redirect('tickets:proactive_alert_list')

    if request.method == 'POST':
        alert.is_addressed = True
        alert.save()
        messages.success(request, f"Allerta per la camera {alert.room.name} segnata come gestita.")

    return redirect('tickets:proactive_alert_list')
