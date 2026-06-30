import json
import logging
from dataclasses import dataclass
from typing import Dict
from urllib.parse import urlparse

from django.conf import settings

try:  # pragma: no cover - optional dependency guard
    from pywebpush import WebPushException, webpush
except ImportError:  # pragma: no cover - handled gracefully in runtime
    WebPushException = Exception  # type: ignore
    webpush = None  # type: ignore

logger = logging.getLogger(__name__)


class PushDeliveryError(Exception):
    """Raised when a push notification cannot be sent."""


@dataclass
class PushPayload:
    title: str
    body: str
    category: str = "general"
    priority: str = "normal"
    icon: str | None = None
    url: str | None = None

    def as_dict(self) -> Dict[str, str]:
        payload = {
            "title": self.title,
            "body": self.body,
            "category": self.category,
            "priority": self.priority,
        }
        if self.icon:
            payload["icon"] = self.icon
        if self.url:
            payload["url"] = self.url
        return payload


def _get_vapid_keys():
    public_key = getattr(settings, "WEB_PUSH_VAPID_PUBLIC_KEY", None)
    private_key = getattr(settings, "WEB_PUSH_VAPID_PRIVATE_KEY", None)
    contact = getattr(settings, "WEB_PUSH_CONTACT_EMAIL", None)

    if not public_key or not private_key:
        raise PushDeliveryError("Le chiavi VAPID non sono configurate")

    if not contact:
        contact = "mailto:admin@localhost"

    return public_key, private_key, contact

def send_push_notification(subscription, payload):
    """Send a push notification immediately using WebPush."""

    if webpush is None:
        raise PushDeliveryError("La libreria pywebpush non è disponibile")

    public_key, private_key, contact = _get_vapid_keys()

    data = payload if isinstance(payload, dict) else payload.as_dict()

    try:
        endpoint_url = urlparse(subscription.endpoint)
        audience = f"{endpoint_url.scheme}://{endpoint_url.netloc}"

        webpush(
            subscription_info=subscription.as_subscription_info(),
            data=json.dumps(data),
            vapid_private_key=private_key,
            vapid_claims={"sub": contact, "aud": audience},
            vapid_public_key=public_key,
        )
    except WebPushException as exc:  # pragma: no cover - depends on external service
        status_code = getattr(getattr(exc, "response", None), "status_code", None)
        if status_code in {404, 410}:
            subscription.is_active = False
            subscription.save(update_fields=["is_active", "updated_at"])
            logger.info(
                "Disattivata la push subscription %s per risposta %s",
                subscription.id,
                status_code,
            )
        raise PushDeliveryError(str(exc)) from exc


def enqueue_notification_push(subscription, payload, *, reason: str | None = None, countdown: int | None = None):
    """Queue a push notification for asynchronous delivery."""

    data = payload if isinstance(payload, dict) else payload.as_dict()

    try:
        from .tasks import deliver_push_notification
    except Exception:  # pragma: no cover - import safeguards for tests/edge cases
        logger.exception(
            "Impossibile importare il task Celery per le notifiche push; invio sincrono di fallback."
        )
        send_push_notification(subscription, data)
        return

    options: Dict[str, int] = {}
    if countdown is not None:
        options["countdown"] = countdown

    deliver_push_notification.apply_async(
        args=[str(subscription.id), data],
        kwargs={"reason": reason},
        **options,
    )

