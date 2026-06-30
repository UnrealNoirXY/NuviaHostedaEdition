import smtplib
from django.template.loader import render_to_string
from django.conf import settings
from django.core.mail import EmailMessage
from django.utils import timezone
from notifications.models import Notification
from accounts.models import User


DEADLINE_NOTIFICATION_ROLES = (
    User.OWNER,
    User.HEAD_MAINTAINER,
    User.MAINTENANCE_MANAGER,
)


def _map_ticket_priority(ticket):
    mapping = {
        ticket.PRIORITY_LOW: Notification.Priority.LOW,
        ticket.PRIORITY_MEDIUM: Notification.Priority.NORMAL,
        ticket.PRIORITY_HIGH: Notification.Priority.HIGH,
        ticket.PRIORITY_URGENT: Notification.Priority.URGENT,
    }
    return mapping.get(ticket.priority, Notification.Priority.NORMAL)

def _dedupe_users(users):
    seen = set()
    ordered = []
    for user in users:
        if user and user.id not in seen:
            seen.add(user.id)
            ordered.append(user)
    return ordered


def send_new_assignment_notification(ticket, absolute_url):
    if not ticket.assigned_to or not ticket.assigned_to.email:
        return

    # Create in-app notification
    Notification.objects.create(
        user=ticket.assigned_to,
        title="Nuovo ticket assegnato",
        message=f"Ti è stato assegnato un nuovo ticket: #{ticket.id} - {ticket.title}",
        body=ticket.description or "",
        link=absolute_url
        ,
        category=Notification.Category.TASK,
        priority=_map_ticket_priority(ticket),
        icon='fa-screwdriver-wrench',
        delivery_channels=['in_app', 'push'],
        source='tickets',
        metadata={'ticket_id': ticket.id, 'event': 'assigned'},
    )

    # Send email notification
    try:
        subject = f"Nuovo ticket di manutenzione assegnato: #{ticket.id} - {ticket.title}"
        context = {'ticket': ticket, 'absolute_url': absolute_url}
        html_body = render_to_string('emails/new_assignment.html', context)

        email = EmailMessage(
            subject,
            html_body,
            settings.DEFAULT_FROM_EMAIL,
            [ticket.assigned_to.email]
        )
        email.content_subtype = "html"
        email.send(fail_silently=False)
    except Exception as e:
        # It's good practice to log this error
        print(f"Failed to send assignment email for ticket #{ticket.id}. Error: {e}")


def send_new_ticket_notification(ticket, recipients, absolute_url):
    recipients = _dedupe_users(recipients)
    if not recipients:
        return

    message = f"È stato aperto un nuovo ticket: #{ticket.id} - {ticket.title}."

    for user in recipients:
        Notification.objects.create(
            user=user,
            title="Nuovo ticket da gestire",
            message=message,
            body=ticket.description or "",
            link=absolute_url,
            category=Notification.Category.TASK,
            priority=_map_ticket_priority(ticket),
            icon='fa-screwdriver-wrench',
            delivery_channels=['in_app', 'push'],
            source='tickets',
            metadata={'ticket_id': ticket.id, 'event': 'created'},
        )

    emails = [user.email for user in recipients if user.email]
    if not emails:
        return

    subject = f"Nuovo ticket di manutenzione: #{ticket.id} - {ticket.title}"
    context = {'ticket': ticket, 'absolute_url': absolute_url}
    html_body = render_to_string('emails/new_ticket_notification.html', context)

    email = EmailMessage(
        subject,
        html_body,
        settings.DEFAULT_FROM_EMAIL,
        emails,
    )
    email.content_subtype = "html"
    email.send(fail_silently=False)


def _claim_notification_recipients(ticket, actor):
    recipients = []
    if ticket.created_by and ticket.created_by != actor:
        recipients.append(ticket.created_by)
    if ticket.assigned_to and ticket.assigned_to != actor:
        recipients.append(ticket.assigned_to)
    return [user for user in _dedupe_users(recipients) if user != actor]


def send_ticket_claim_notification(ticket, claimant, absolute_url):
    recipients = _claim_notification_recipients(ticket, claimant)
    if not recipients:
        return

    message = f"{claimant.get_full_name() or claimant.username} ha preso in carico il ticket #{ticket.id}."

    for user in recipients:
        Notification.objects.create(
            user=user,
            title="Ticket preso in carico",
            message=message,
            link=absolute_url,
            category=Notification.Category.TASK,
            priority=_map_ticket_priority(ticket),
            icon='fa-handshake-simple',
            delivery_channels=['in_app', 'push'],
            source='tickets',
            metadata={'ticket_id': ticket.id, 'event': 'claimed'},
        )

    emails = [user.email for user in recipients if user.email]
    if not emails:
        return

    context = {'ticket': ticket, 'claimant': claimant, 'absolute_url': absolute_url}
    subject = f"Ticket #{ticket.id} preso in carico"
    html_message = render_to_string('emails/ticket_claimed.html', context)

    email = EmailMessage(subject, html_message, settings.DEFAULT_FROM_EMAIL, emails)
    email.content_subtype = "html"
    email.send(fail_silently=False)


def send_ticket_release_notification(ticket, releaser, absolute_url):
    recipients = _claim_notification_recipients(ticket, releaser)
    if not recipients:
        return

    message = f"{releaser.get_full_name() or releaser.username} ha rilasciato il ticket #{ticket.id}."

    for user in recipients:
        Notification.objects.create(
            user=user,
            title="Ticket disponibile",
            message=message,
            link=absolute_url,
            category=Notification.Category.ALERT,
            priority=_map_ticket_priority(ticket),
            icon='fa-users-gear',
            delivery_channels=['in_app', 'push'],
            source='tickets',
            metadata={'ticket_id': ticket.id, 'event': 'released'},
        )

    emails = [user.email for user in recipients if user.email]
    if not emails:
        return

    context = {'ticket': ticket, 'releaser': releaser, 'absolute_url': absolute_url}
    subject = f"Ticket #{ticket.id} è di nuovo disponibile"
    html_message = render_to_string('emails/ticket_released.html', context)

    email = EmailMessage(subject, html_message, settings.DEFAULT_FROM_EMAIL, emails)
    email.content_subtype = "html"
    email.send(fail_silently=False)


def send_status_change_notification(ticket, old_status, new_status, absolute_url):
    recipients_users = []
    if ticket.created_by:
        recipients_users.append(ticket.created_by)
    if ticket.assigned_to and ticket.assigned_to not in recipients_users:
        recipients_users.append(ticket.assigned_to)

    if not recipients_users:
        return

    # Create in-app notifications
    message = f"Lo stato del ticket #{ticket.id} è cambiato da '{old_status}' a '{new_status}'."
    for user in recipients_users:
        Notification.objects.create(
            user=user,
            title="Ticket aggiornato",
            message=message,
            link=absolute_url,
            category=Notification.Category.ALERT,
            priority=_map_ticket_priority(ticket),
            icon='fa-arrows-rotate',
            delivery_channels=['in_app', 'push'],
            source='tickets',
            metadata={'ticket_id': ticket.id, 'event': 'status_change'},
        )

    # Send emails
    email_recipients = [user.email for user in recipients_users if user.email]
    if not email_recipients:
        return

    subject = f"Aggiornamento stato ticket #{ticket.id}: {ticket.title}"
    context = {
        'ticket': ticket,
        'old_status': old_status,
        'new_status': new_status,
    }
    html_message = render_to_string('emails/status_change.html', context)

    email = EmailMessage(
        subject,
        html_message,
        settings.DEFAULT_FROM_EMAIL,
        email_recipients
    )
    email.content_subtype = "html"
    email.send(fail_silently=False)


def send_new_comment_notification(comment, absolute_url):
    ticket = comment.ticket
    author = comment.author

    recipients_users = []
    # Notify creator if they aren't the one who commented
    if ticket.created_by and ticket.created_by != author:
        recipients_users.append(ticket.created_by)
    # Notify assignee if they aren't the one who commented
    if ticket.assigned_to and ticket.assigned_to != author and ticket.assigned_to not in recipients_users:
        recipients_users.append(ticket.assigned_to)

    if not recipients_users:
        return

    # Create in-app notifications
    message = f"Nuovo commento da {author.username} sul ticket #{ticket.id}."
    for user in recipients_users:
        Notification.objects.create(
            user=user,
            title="Nuovo commento",
            message=message,
            link=absolute_url,
            category=Notification.Category.TASK,
            priority=_map_ticket_priority(ticket),
            icon='fa-comments',
            delivery_channels=['in_app', 'push'],
            source='tickets',
            metadata={'ticket_id': ticket.id, 'event': 'comment'},
        )

    # Send emails
    email_recipients = [user.email for user in recipients_users if user.email]
    if not email_recipients:
        return

    subject = f"Nuovo commento sul ticket #{ticket.id}: {ticket.title}"
    context = {'ticket': ticket, 'comment': comment, 'absolute_url': absolute_url}
    html_message = render_to_string('emails/new_comment.html', context)

    email = EmailMessage(
        subject,
        html_message,
        settings.DEFAULT_FROM_EMAIL,
        email_recipients
    )
    email.content_subtype = "html"
    email.send(fail_silently=False)


def send_deadline_reminder_notification(ticket, absolute_url):
    """Invia promemoria a tre ore dalla scadenza del ticket."""

    recipients = []
    if ticket.assigned_to:
        recipients.append(ticket.assigned_to)

    if ticket.resort and ticket.resort.company:
        managers = ticket.resort.company.users.filter(role__in=DEADLINE_NOTIFICATION_ROLES)
        recipients.extend(list(managers))

    # Deduplica preservando l'ordine
    unique_recipients = []
    seen_ids = set()
    for user in recipients:
        if user and user.id not in seen_ids:
            seen_ids.add(user.id)
            unique_recipients.append(user)

    if not unique_recipients:
        return

    formatted_due = timezone.localtime(ticket.due_date).strftime('%d/%m/%Y %H:%M')
    message = f"Il ticket #{ticket.id} - {ticket.title} scadrà alle {formatted_due}."

    for user in unique_recipients:
        Notification.objects.create(
            user=user,
            title="Promemoria scadenza ticket",
            message=message,
            link=absolute_url,
            category=Notification.Category.ALERT,
            priority=Notification.Priority.HIGH,
            icon='fa-hourglass-half',
            delivery_channels=['in_app', 'push'],
            source='tickets',
            metadata={'ticket_id': ticket.id, 'event': 'deadline_reminder'},
        )

    email_recipients = [user.email for user in unique_recipients if user.email]
    if not email_recipients:
        return

    context = {'ticket': ticket, 'absolute_url': absolute_url, 'formatted_due': formatted_due}
    subject = f"Promemoria scadenza ticket #{ticket.id}"
    html_message = render_to_string('emails/deadline_reminder.html', context)

    email = EmailMessage(
        subject,
        html_message,
        settings.DEFAULT_FROM_EMAIL,
        email_recipients
    )
    email.content_subtype = "html"
    email.send(fail_silently=False)


def send_unassigned_ticket_notification(ticket, recipients, absolute_url):
    eligible = []
    for user in recipients:
        if not user:
            continue
        if hasattr(user, 'receives_unassigned_ticket_alerts') and not user.receives_unassigned_ticket_alerts:
            continue
        eligible.append(user)

    eligible = _dedupe_users(eligible)
    if not eligible:
        return

    formatted_due = None
    if ticket.due_date:
        formatted_due = timezone.localtime(ticket.due_date).strftime('%d/%m/%Y %H:%M')

    body = f"Il ticket #{ticket.id} - {ticket.title} è in attesa di presa in carico."
    if formatted_due:
        body += f" Scade il {formatted_due}."

    for user in eligible:
        Notification.objects.create(
            user=user,
            title="Ticket non assegnato",
            message=body,
            link=absolute_url,
            category=Notification.Category.ALERT,
            priority=_map_ticket_priority(ticket),
            icon='fa-person-running',
            delivery_channels=['in_app', 'push'],
            source='tickets',
            metadata={'ticket_id': ticket.id, 'event': 'unassigned_alert'},
        )

    emails = [user.email for user in eligible if user.email]
    if not emails:
        return

    context = {'ticket': ticket, 'absolute_url': absolute_url, 'formatted_due': formatted_due}
    subject = f"Ticket #{ticket.id} in attesa di presa in carico"
    html_message = render_to_string('emails/unassigned_ticket_alert.html', context)
    email = EmailMessage(subject, html_message, settings.DEFAULT_FROM_EMAIL, emails)
    email.content_subtype = "html"
    email.send(fail_silently=False)
