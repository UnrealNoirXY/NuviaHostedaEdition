from django.conf import settings
from django.core.mail import EmailMultiAlternatives, get_connection
from django.template.loader import render_to_string
from django.utils import timezone

from .models import ProfileCardDelivery


def send_profile_card_email(*, card, public_url, recipient_email, created_by=None):
    delivery = ProfileCardDelivery.objects.create(
        card=card,
        recipient_email=recipient_email,
        created_by=created_by,
        status=ProfileCardDelivery.STATUS_PENDING,
        attempts=1,
    )

    connection = get_connection(
        host=settings.EMAIL_HOST,
        port=settings.EMAIL_PORT,
        username=settings.EMAIL_HOST_USER,
        password=settings.EMAIL_HOST_PASSWORD,
        use_tls=settings.EMAIL_USE_TLS,
        use_ssl=settings.EMAIL_USE_SSL,
    )

    context = {"card": card, "public_url": public_url}
    subject = f"Scheda contatto: {card.first_name} {card.last_name}"
    text_body = render_to_string("profile_cards/emails/profile_card_email.txt", context)
    html_body = render_to_string("profile_cards/emails/profile_card_email.html", context)

    email = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[recipient_email],
        connection=connection,
    )
    email.attach_alternative(html_body, "text/html")

    try:
        email.send(fail_silently=False)
    except Exception as exc:  # noqa: BLE001
        delivery.status = ProfileCardDelivery.STATUS_FAILED
        delivery.last_error = str(exc)
        delivery.save(update_fields=["status", "last_error"])
        return delivery

    delivery.status = ProfileCardDelivery.STATUS_SENT
    delivery.sent_at = timezone.now()
    delivery.save(update_fields=["status", "sent_at"])
    return delivery


def send_lead_notification_email(*, lead):
    connection = get_connection(
        host=settings.EMAIL_HOST,
        port=settings.EMAIL_PORT,
        username=settings.EMAIL_HOST_USER,
        password=settings.EMAIL_HOST_PASSWORD,
        use_tls=settings.EMAIL_USE_TLS,
        use_ssl=settings.EMAIL_USE_SSL,
    )

    context = {"lead": lead}
    subject = f"Nuovo messaggio da {lead.name} via Noir Card"
    text_body = render_to_string("profile_cards/emails/lead_notification.txt", context)
    html_body = render_to_string("profile_cards/emails/lead_notification.html", context)

    email = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[lead.card.email],
        connection=connection,
    )
    email.attach_alternative(html_body, "text/html")

    try:
        email.send(fail_silently=False)
        return True
    except Exception:
        return False
