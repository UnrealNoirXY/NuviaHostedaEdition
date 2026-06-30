import logging
import time
from typing import List, Optional, Sequence, Tuple

from django.conf import settings
from django.core.mail import EmailMultiAlternatives, get_connection

from prometheus_client import Counter, Histogram

from communications.models import EmailLog

logger = logging.getLogger(__name__)

EMAIL_SEND_COUNTER = Counter(
    "email_gateway_send_total",
    "Totale invii email per stato",
    labelnames=["status", "reason"],
)
EMAIL_SEND_LATENCY = Histogram(
    "email_gateway_send_seconds",
    "Durata invio email",
    buckets=(0.1, 0.25, 0.5, 1, 2, 5, 10),
)


class EmailGateway:
    """Gateway centralizzato per inviare email con timeout e metriche."""

    def __init__(self, timeout: Optional[int] = None):
        self.timeout = timeout or getattr(settings, "EMAIL_TIMEOUT", 10)

    def send_email(
        self,
        *,
        subject: str,
        text_body: str,
        html_body: Optional[str],
        recipients: Sequence[str],
        attachments: Optional[List[Tuple[str, bytes, str]]] = None,
        headers: Optional[dict] = None,
    ) -> int:
        start_time = time.monotonic()
        try:
            connection = get_connection(timeout=self.timeout)
            message = EmailMultiAlternatives(
                subject,
                text_body,
                settings.DEFAULT_FROM_EMAIL,
                list(recipients),
                connection=connection,
                headers=headers,
            )
            if html_body:
                message.attach_alternative(html_body, "text/html")
            for attachment in attachments or []:
                message.attach(*attachment)
            sent = message.send(fail_silently=False)
            EMAIL_SEND_COUNTER.labels(status="success", reason="").inc()
            return sent
        except Exception as exc:  # pragma: no cover - metric/log covered in tests
            logger.exception("Errore durante l'invio email: %s", exc)
            EMAIL_SEND_COUNTER.labels(status="failure", reason=exc.__class__.__name__).inc()
            raise
        finally:
            EMAIL_SEND_LATENCY.observe(time.monotonic() - start_time)


def log_email_outcome(
    *,
    task_name: str,
    recipient: str,
    status: EmailLog.Status,
    booking=None,
    error_message: str = "",
    link_used: str = "",
    celery_task_id: str = "",
    payload: Optional[dict] = None,
):
    EmailLog.objects.create(
        task_name=task_name,
        recipient=recipient,
        status=status,
        booking=booking,
        error_message=error_message[:2000],
        link_used=link_used,
        celery_task_id=celery_task_id,
        payload=payload,
    )


def dispatch_email_task(task, *args, **kwargs):
    """Enqueue a celery task with graceful fallback when broker is down."""
    try:
        return task.apply_async(args=args, kwargs=kwargs)
    except Exception as exc:  # pragma: no cover - fallback path asserted in tests
        logger.warning("Broker Celery non raggiungibile, eseguo sincrono: %s", exc)
        return task.apply(args=args, kwargs=kwargs)
