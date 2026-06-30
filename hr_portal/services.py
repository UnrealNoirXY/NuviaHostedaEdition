from __future__ import annotations

import logging
import smtplib
import socket
import time
from datetime import timedelta
from dataclasses import dataclass
from typing import TYPE_CHECKING, Iterable, List, Optional, Tuple

from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import EmailMultiAlternatives, send_mail
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone
from django.core import signing

from accounts.models import UserPrivacyConsent

from .observability import emit_structured_log, metrics, record_latency

if TYPE_CHECKING:  # pragma: no cover
    from .models import HRNotification, HRNotificationDelivery, NotificationPreference


logger = logging.getLogger(__name__)


def describe_email_error(exc):
    if isinstance(exc, smtplib.SMTPAuthenticationError):
        detail = getattr(exc, "smtp_error", "") or "Credenziali SMTP non valide."
        if isinstance(detail, bytes):
            detail = detail.decode(errors="ignore")
        return f"SMTP auth failed: {detail}"
    if isinstance(exc, smtplib.SMTPConnectError):
        return "SMTP connection failed: impossibile connettersi al server SMTP."
    if isinstance(exc, smtplib.SMTPServerDisconnected):
        return "SMTP disconnected: connessione al server interrotta."
    if isinstance(exc, smtplib.SMTPRecipientsRefused):
        refused = getattr(exc, "recipients", None) or {}
        if refused:
            return f"SMTP recipients refused: {', '.join(refused.keys())}"
        return "SMTP recipients refused: destinatario rifiutato dal server."
    if isinstance(exc, smtplib.SMTPDataError):
        detail = getattr(exc, "smtp_error", "") or "Errore nei dati inviati al server SMTP."
        if isinstance(detail, bytes):
            detail = detail.decode(errors="ignore")
        return f"SMTP data error: {detail}"
    if isinstance(exc, socket.gaierror):
        return "SMTP host unreachable: errore DNS o host non raggiungibile."
    if isinstance(exc, TimeoutError):
        return "SMTP timeout: il server non ha risposto in tempo."
    return str(exc) or exc.__class__.__name__


@dataclass
class DeliveryResult:
    deliveries: List[HRNotificationDelivery]
    errors: List[str]


def _within_quiet_hours(pref, now) -> bool:
    if not pref.quiet_hours_start or not pref.quiet_hours_end:
        return False

    start = pref.quiet_hours_start
    end = pref.quiet_hours_end
    current = now.time()

    if start <= end:
        return start <= current <= end
    return current >= start or current <= end


def _eligible_recipients(notification):
    User = get_user_model()
    filters = Q(is_active=True)

    if notification.audience_company_id:
        filters &= Q(company_id=notification.audience_company_id)
    if notification.audience_resort_id:
        filters &= Q(resort_id=notification.audience_resort_id)
    if notification.audience_roles:
        filters &= Q(role__in=notification.audience_roles)

    return User.objects.filter(filters)


def _deliver_email(notification, user, pref) -> Tuple[bool, Optional[str]]:
    if not pref.allow_email:
        return False, "email_disabled"
    if not getattr(user, "email", None):
        return False, "missing_email"

    try:
        send_mail(
            subject=f"{getattr(settings, 'HR_EMAIL_SUBJECT_PREFIX', '[HR] ')}{notification.title}",
            message=notification.body,
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
            recipient_list=[user.email],
            fail_silently=False,
        )
        return True, None
    except Exception as exc:  # pragma: no cover - email backend/runtime specific
        logger.warning("Failed to send HR notification email", exc_info=exc)
        return False, str(exc)


def _deliver_stub(channel: str, pref_field: str, pref) -> Tuple[bool, Optional[str]]:
    if not getattr(pref, pref_field, False):
        return False, f"{channel}_disabled"
    return False, "channel_not_configured"


def _ensure_preference(user):
    Preference = apps.get_model("hr_portal", "NotificationPreference")
    pref, _ = Preference.objects.get_or_create(user=user)
    return pref


def deliver_notification(notification) -> DeliveryResult:
    now = timezone.now()
    deliveries: List[HRNotificationDelivery] = []
    errors: List[str] = []

    recipients = _eligible_recipients(notification)
    metrics.increment(
        "hr_notification.recipient_candidates",
        recipients.count(),
        notification_id=str(notification.id),
    )
    Delivery = apps.get_model("hr_portal", "HRNotificationDelivery")
    EventLog = apps.get_model("hr_portal", "HREventLog")

    with record_latency("hr_notification.delivery_latency_ms", notification_id=str(notification.id)):
        for user in recipients:
            pref = _ensure_preference(user)
            if _within_quiet_hours(pref, now):
                delivery, _ = Delivery.objects.get_or_create(
                    notification=notification,
                    user=user,
                    channel=Delivery.CHANNEL_EMAIL,
                    defaults={"status": Delivery.STATUS_SKIPPED, "error": "quiet_hours"},
                )
                deliveries.append(delivery)
                metrics.increment(
                    "hr_notification.suppressed",
                    notification_id=str(notification.id),
                    reason="quiet_hours",
                )
                continue

            channels = [
                (Delivery.CHANNEL_EMAIL, _deliver_email, None),
                (Delivery.CHANNEL_PUSH, _deliver_stub, "allow_push"),
                (Delivery.CHANNEL_SMS, _deliver_stub, "allow_sms"),
            ]

            for channel, handler, pref_field in channels:
                delivery, _ = Delivery.objects.get_or_create(
                    notification=notification,
                    user=user,
                    channel=channel,
                    defaults={"status": Delivery.STATUS_PENDING},
                )

                if delivery.status == Delivery.STATUS_DELIVERED:
                    deliveries.append(delivery)
                    continue

                success, error_message = (
                    handler(notification, user, pref) if not pref_field else handler(channel, pref_field, pref)
                )

                if success:
                    delivery.status = Delivery.STATUS_DELIVERED
                    delivery.sent_at = now
                    delivery.error = ""
                    metrics.increment("hr_notification.delivered", notification_id=str(notification.id), channel=channel)
                else:
                    delivery.status = Delivery.STATUS_FAILED if error_message != "" else delivery.status
                    delivery.error = error_message or ""
                    if error_message:
                        metrics.increment(
                            "hr_notification.failed", notification_id=str(notification.id), channel=channel
                        )

                delivery.save(update_fields=["status", "sent_at", "error"])
                deliveries.append(delivery)

                if success:
                    EventLog.record(
                        event_type="notification_delivered",
                        actor=notification.created_by,
                        target=notification,
                        metadata={"channel": channel, "user_id": str(user.id)},
                    )
                elif error_message:
                    EventLog.record(
                        event_type="notification_delivery_failed",
                        actor=notification.created_by,
                        target=notification,
                        metadata={"channel": channel, "user_id": str(user.id), "error": error_message},
                    )
                    errors.append(error_message)

    notification.delivered_count = Delivery.objects.filter(
        notification=notification, status=Delivery.STATUS_DELIVERED
    ).values("user").distinct().count()
    notification.save(update_fields=["delivered_count", "updated_at"])

    emit_structured_log(
        "notification.delivery.summary",
        notification_id=str(notification.id),
        delivered=notification.delivered_count,
        errors=len(errors),
    )

    return DeliveryResult(deliveries=deliveries, errors=errors)


from django.template.loader import render_to_string
from django.utils.html import strip_tags


def notify_payslip_ready(user, payslip):
    latest_consent = (
        UserPrivacyConsent.objects.filter(user=user)
        .order_by("-accepted_at", "-created_at")
        .first()
    )
    if not latest_consent or not latest_consent.email_confirmed_at:
        EventLog = apps.get_model("hr_portal", "HREventLog")
        EventLog.record(
            event_type="payslip_notification_blocked",
            actor=None,
            target=payslip,
            metadata={"user_id": str(user.id), "reason": "email_not_confirmed"},
        )
        return False, "email_not_confirmed"
    if not latest_consent.payslip_email_opt_in:
        EventLog = apps.get_model("hr_portal", "HREventLog")
        EventLog.record(
            event_type="payslip_notification_blocked",
            actor=None,
            target=payslip,
            metadata={"user_id": str(user.id), "reason": "payslip_email_opt_out"},
        )
        return False, "payslip_email_opt_out"

    pref = _ensure_preference(user)
    now = timezone.now()
    if _within_quiet_hours(pref, now) or not pref.allow_email:
        return False, "suppressed"
    if not getattr(user, "email", None):
        return False, "missing_email"

    try:
        signed_url, expires_at = build_signed_payslip_url(payslip_id=payslip.id, user_id=user.id)
        context = {
            'user': user,
            'payslip': payslip,
            'profile_url': signed_url,
            'site_name': settings.JAZZMIN_SETTINGS['site_brand'],
        }

        html_message = render_to_string('hr_portal/emails/payslip_notification.html', context)
        plain_message = strip_tags(html_message)

        success, error_message, attempts = _send_with_retry(
            lambda: send_mail(
                subject=f"Busta Paga di {payslip.period_label} Pronta per Te",
                message=plain_message,
                html_message=html_message,
                from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
                recipient_list=[user.email],
                fail_silently=False,
            ),
            max_attempts=getattr(settings, "HR_EMAIL_MAX_RETRIES", 3),
            base_delay=getattr(settings, "HR_EMAIL_RETRY_BASE_DELAY", 1.0),
        )
        if not success:
            raise RuntimeError(error_message or "Errore invio email busta paga")
        EventLog = apps.get_model("hr_portal", "HREventLog")
        EventLog.record(
            event_type="payslip_notified",
            actor=None,
            target=payslip,
            metadata={
                "user_id": str(user.id),
                "email": user.email,
                "attempts": attempts,
                "signed_url_expires_at": expires_at.isoformat(),
            },
        )
        emit_structured_log(
            "payslip.notification.sent",
            payslip_id=str(payslip.id),
            user_id=str(user.id),
            company_id=str(getattr(payslip, "company_id", "")),
            resort_id=str(getattr(payslip, "resort_id", "")),
        )
        metrics.increment("payslip.notification.sent", company_id=str(getattr(payslip, "company_id", "")))
        return True, None
    except Exception as exc:  # pragma: no cover
        logger.warning("Failed to notify payslip availability", exc_info=exc)
        EventLog = apps.get_model("hr_portal", "HREventLog")
        EventLog.record(
            event_type="payslip_notification_failed",
            actor=None,
            target=payslip,
            metadata={
                "user_id": str(user.id),
                "email": getattr(user, "email", ""),
                "error": describe_email_error(exc),
            },
        )
        return False, describe_email_error(exc)


def send_payslip_email(
    *,
    recipient_email,
    subject,
    body,
    attachment_name,
    attachment_bytes,
    context=None,
    connection=None,
    from_email=None,
):
    try:
        template_context = {
            "subject": subject,
            "body": body,
            "recipient_email": recipient_email,
            "attachment_name": attachment_name,
            **(context or {}),
        }
        download_url = template_context.get("download_url")
        if download_url:
            template_context["body"] = f"{body}\n\nScarica la busta paga: {download_url}"
        html_message = render_to_string("hr_portal/emails/payslip_send.html", template_context)
        plain_message = strip_tags(html_message)

        email = EmailMultiAlternatives(
            subject=subject,
            body=plain_message,
            from_email=from_email or getattr(settings, "DEFAULT_FROM_EMAIL", None),
            to=[recipient_email],
            connection=connection,
        )
        email.attach_alternative(html_message, "text/html")
        email.attach(attachment_name, attachment_bytes, "application/pdf")
        success, error_message, attempts = _send_with_retry(
            lambda: email.send(fail_silently=False),
            max_attempts=getattr(settings, "HR_EMAIL_MAX_RETRIES", 3),
            base_delay=getattr(settings, "HR_EMAIL_RETRY_BASE_DELAY", 1.0),
        )
        return success, error_message, attempts
    except Exception as exc:  # pragma: no cover - email backend/runtime specific
        logger.warning("Failed to send payslip email", exc_info=exc)
        return False, describe_email_error(exc), 1


def _send_with_retry(send_fn, *, max_attempts=3, base_delay=1.0):
    last_error = None
    attempts = 0
    for attempt in range(1, max_attempts + 1):
        attempts = attempt
        try:
            send_fn()
            return True, None, attempts
        except Exception as exc:  # pragma: no cover - depends on backend
            last_error = describe_email_error(exc)
            if attempt < max_attempts:
                time.sleep(base_delay * (2 ** (attempt - 1)))
    return False, last_error or "Errore SMTP sconosciuto.", attempts


def build_signed_payslip_url(*, payslip_id, user_id, max_age=None):
    signer = signing.TimestampSigner(salt="hr.payslip.download")
    payload = f"{payslip_id}:{user_id}"
    token = signer.sign(payload)
    expires_in = max_age or getattr(settings, "HR_SIGNED_LINK_MAX_AGE_SECONDS", 60 * 60 * 24 * 2)
    expires_at = timezone.now() + timedelta(seconds=expires_in)
    download_path = reverse("hr_portal:download_payslip", args=[payslip_id])
    signed_url = f"{settings.BASE_URL}{download_path}?token={token}"
    return signed_url, expires_at
