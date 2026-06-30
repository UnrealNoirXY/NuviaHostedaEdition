from celery import shared_task
from django.template.loader import render_to_string
from django.utils import timezone
from datetime import timedelta
from django.conf import settings
from types import SimpleNamespace

from .models import ScheduledEmailReport
from reviews.pdf_generator import generate_report_pdf
from communications.email_gateway import EmailGateway, log_email_outcome
from communications.models import EmailLog

email_gateway = EmailGateway()

@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_jitter=True, retry_kwargs={'max_retries': 5})
def send_review_report(self, report_id, start_date_str=None, end_date_str=None):
    """
    Celery task to generate a PDF review report and send it as an email attachment.
    """
    try:
        report_config = ScheduledEmailReport.objects.get(id=report_id)
    except ScheduledEmailReport.DoesNotExist:
        return f"ScheduledEmailReport with id={report_id} not found."

    # Determine the date range
    today = timezone.now().date()
    if start_date_str and end_date_str:
        start_date = timezone.datetime.fromisoformat(start_date_str).date()
        end_date = timezone.datetime.fromisoformat(end_date_str).date()
        date_for_filename = end_date
    else:
        days_to_subtract = report_config.review_period_days
        end_date = today
        start_date = end_date - timedelta(days=days_to_subtract)
        date_for_filename = start_date if days_to_subtract == 1 else today

    # Prepare data for the PDF generator
    filters = {
        'resorts': list(report_config.resorts.values_list('id', flat=True)),
        'start_date': start_date.isoformat(),
        'end_date': end_date.isoformat(),
    }

    # Create a mock template object for the PDF generator
    template_obj = SimpleNamespace(
        name=report_config.name,
        filters=filters
    )

    # Get base URL from settings for building URLs inside the PDF
    base_url = settings.BASE_URL

    # Generate the PDF in memory
    pdf_file = generate_report_pdf(template_obj, base_url)
    if not pdf_file:
        return f"Failed to generate PDF for report '{report_config.name}'."

    pdf_filename = f"Report_Del_Giorno_{date_for_filename.strftime('%d_%m_%Y')}.pdf"

    # Send the email with the PDF attachment
    recipient_list = [user.email for user in report_config.recipients.all() if user.email]
    if not recipient_list:
        return f"Report '{report_config.name}' has no recipients with valid email addresses."

    subject = f"Report Programmato: {report_config.name} del {date_for_filename.strftime('%d/%m/%Y')}"

    html_body = render_to_string(
        'emails/pdf_notification_email.html',
        {'report_name': report_config.name}
    )

    try:
        email_gateway.send_email(
            subject=subject,
            text_body=html_body,
            html_body=html_body,
            recipients=recipient_list,
            attachments=[(pdf_filename, pdf_file, 'application/pdf')],
        )
        for recipient in recipient_list:
            log_email_outcome(
                task_name='send_review_report',
                recipient=recipient,
                status=EmailLog.Status.SUCCESS,
                payload={'report_id': report_id},
                celery_task_id=self.request.id,
            )
        return f"Successfully sent report '{report_config.name}' to {len(recipient_list)} recipients."
    except Exception as e:
        for recipient in recipient_list or ["unknown"]:
            log_email_outcome(
                task_name='send_review_report',
                recipient=recipient,
                status=EmailLog.Status.FAILED,
                error_message=str(e),
                payload={'report_id': report_id},
                celery_task_id=self.request.id,
            )
        raise


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_jitter=True, retry_kwargs={'max_retries': 5})
def send_event_invitation_email(self, invitation_id):
    """
    Celery task to send an email notification for a new event invitation.
    """
    from desk.models import EventInvitation
    try:
        invitation = EventInvitation.objects.select_related('event', 'invitee', 'event__user').get(id=invitation_id)
    except EventInvitation.DoesNotExist:
        return f"EventInvitation with id={invitation_id} not found."

    recipient_email = invitation.invitee.email
    if not recipient_email:
        return f"Invitee {invitation.invitee.username} has no email address."

    subject = f"Sei stato invitato a un evento: {invitation.event.title}"

    context = {
        'invitation': invitation,
        'event': invitation.event,
        'creator': invitation.event.user,
        'base_url': settings.BASE_URL,
    }

    html_body = render_to_string('emails/event_invitation_email.html', context)

    try:
        email_gateway.send_email(
            subject=subject,
            text_body=html_body,
            html_body=html_body,
            recipients=[recipient_email],
        )
        log_email_outcome(
            task_name='send_event_invitation_email',
            recipient=recipient_email,
            status=EmailLog.Status.SUCCESS,
            payload={'invitation_id': invitation_id},
            celery_task_id=self.request.id,
        )
        return f"Successfully sent invitation for event '{invitation.event.title}' to {recipient_email}."
    except Exception as e:
        log_email_outcome(
            task_name='send_event_invitation_email',
            recipient=recipient_email or "unknown",
            status=EmailLog.Status.FAILED,
            error_message=str(e),
            payload={'invitation_id': invitation_id},
            celery_task_id=self.request.id,
        )
        raise
