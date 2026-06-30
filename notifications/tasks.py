import logging
from typing import Any, Dict

from celery import shared_task
from celery.exceptions import MaxRetriesExceededError

from .models import PushSubscription
from .push import PushDeliveryError, send_push_notification

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=5)
def deliver_push_notification(self, subscription_id: str, payload: Dict[str, Any], reason: str | None = None):
    """Deliver a push notification with retry and exponential backoff."""

    try:
        subscription = PushSubscription.objects.get(id=subscription_id)
    except PushSubscription.DoesNotExist:
        logger.info(
            "Subscription %s inesistente: nessuna notifica push inviata.",
            subscription_id,
            extra={"subscription_id": subscription_id, "reason": reason},
        )
        return {"status": "missing"}

    if not subscription.is_active:
        logger.info(
            "Subscription %s inattiva: invio push ignorato.",
            subscription_id,
            extra={"subscription_id": subscription_id, "reason": reason},
        )
        return {"status": "inactive"}

    try:
        send_push_notification(subscription, payload)
    except PushDeliveryError as exc:
        attempt = self.request.retries + 1
        countdown = min(2 ** attempt * 60, 3600)
        logger.warning(
            "Invio push tentativo %s per subscription %s fallito: %s",
            attempt,
            subscription_id,
            exc,
            extra={"subscription_id": subscription_id, "reason": reason},
        )
        try:
            raise self.retry(exc=exc, countdown=countdown)
        except MaxRetriesExceededError:
            logger.error(
                "Invio push per subscription %s fallito definitivamente dopo %s tentativi: %s",
                subscription_id,
                attempt,
                exc,
                extra={"subscription_id": subscription_id, "reason": reason},
            )
            return {"status": "failed", "error": str(exc)}

    logger.info(
        "Notifica push inviata con successo a %s.",
        subscription_id,
        extra={"subscription_id": subscription_id, "reason": reason},
    )
    return {"status": "sent"}
