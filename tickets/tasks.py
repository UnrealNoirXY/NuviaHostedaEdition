from celery import shared_task
from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from django.db.models import Count, Q
from accounts.models import User
from .models import Ticket, ProactiveMaintenanceAlert
from .emails import send_deadline_reminder_notification, send_unassigned_ticket_notification
from resort.models import Room

@shared_task
def analyze_ticket_patterns():
    """
    Analyzes recent tickets to find rooms with recurring issues and creates proactive alerts.
    """
    thirty_days_ago = timezone.now() - timezone.timedelta(days=30)

    # Find rooms with more than 2 tickets in the last 30 days.
    # We only consider rooms that do not already have an open alert.
    problematic_rooms = Room.objects.annotate(
        recent_ticket_count=Count('tickets', filter=Q(tickets__created_at__gte=thirty_days_ago))
    ).filter(
        recent_ticket_count__gt=2,
        proactive_alerts__is_addressed=True
    ).distinct()

    # We also need to get rooms that have more than 2 tickets but NO alerts at all.
    # This is a bit more complex. Let's simplify for now and handle all rooms, then filter.

    all_problematic_rooms = Room.objects.annotate(
        recent_ticket_count=Count('tickets', filter=Q(tickets__created_at__gte=thirty_days_ago))
    ).filter(recent_ticket_count__gt=2)

    alerts_created_count = 0
    for room in all_problematic_rooms:
        # Check if an unaddressed alert for this room already exists.
        if not ProactiveMaintenanceAlert.objects.filter(room=room, is_addressed=False).exists():
            last_ticket = room.tickets.filter(created_at__gte=thirty_days_ago).latest('created_at')

            ProactiveMaintenanceAlert.objects.create(
                room=room,
                reason=f"{room.recent_ticket_count} tickets in the last 30 days.",
                last_ticket=last_ticket
            )
            alerts_created_count += 1

    return f"Analysis complete. Created {alerts_created_count} new proactive alerts."


@shared_task
def send_ticket_deadline_reminders():
    """Invia promemoria per i ticket in scadenza entro tre ore."""

    now = timezone.now()
    horizon = now + timezone.timedelta(hours=3)

    tickets_to_remind = list(Ticket.objects.filter(
        due_date__isnull=False,
        due_date__gt=now,
        due_date__lte=horizon,
        status__in=['open', 'in_progress', 'resolved'],
        deadline_reminder_sent_at__isnull=True,
    ).select_related('resort__company', 'assigned_to'))

    for ticket in tickets_to_remind:
        absolute_url = f"{settings.BASE_URL}{reverse('ticket_detail', args=[ticket.id])}"
        send_deadline_reminder_notification(ticket, absolute_url)
        ticket.deadline_reminder_sent_at = now
        ticket.save(update_fields=['deadline_reminder_sent_at'])

    return f"Inviati {len(tickets_to_remind)} promemoria scadenza"


@shared_task
def send_unassigned_ticket_broadcasts():
    """Avvisa i manutentori dei ticket ancora senza presa in carico."""

    now = timezone.now()
    stale_threshold = now - timezone.timedelta(hours=6)

    tickets_to_notify = list(
        Ticket.objects.filter(
            assigned_to__isnull=True,
            status__in=['open', 'in_progress'],
        )
        .filter(Q(unassigned_notification_sent_at__isnull=True) | Q(unassigned_notification_sent_at__lt=stale_threshold))
        .select_related('resort__company')
    )

    sent = 0
    for ticket in tickets_to_notify:
        recipients = []
        if ticket.resort_id:
            recipients.extend(
                User.objects.filter(
                    resort=ticket.resort,
                    role__in=[User.MAINTAINER, User.HEAD_MAINTAINER],
                )
            )
            if ticket.resort.company_id:
                recipients.extend(
                    User.objects.filter(
                        company=ticket.resort.company,
                        role__in=[User.MAINTENANCE_MANAGER, User.OWNER],
                    )
                )

        if not recipients:
            continue

        absolute_url = f"{settings.BASE_URL}{reverse('ticket_detail', args=[ticket.id])}"
        send_unassigned_ticket_notification(ticket, recipients, absolute_url)
        ticket.unassigned_notification_sent_at = now
        ticket.save(update_fields=['unassigned_notification_sent_at'])
        sent += 1

    return f"Inviati {sent} avvisi ticket non assegnati"
