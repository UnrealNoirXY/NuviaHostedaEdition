import logging
from typing import Iterable, Sequence

from django.db.models import Q
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Notification, PushSubscription
from .push import enqueue_notification_push

logger = logging.getLogger(__name__)


def _normalize_channels(channels: Sequence[str] | str | None) -> set[str]:
    if not channels:
        return set()
    if isinstance(channels, str):
        return {channels}
    return {channel for channel in channels if channel}


def _subscriptions_for_notification(notification: Notification) -> Iterable[PushSubscription]:
    subscriptions = PushSubscription.objects.filter(is_active=True).select_related("user")

    if notification.user_id:
        return subscriptions.filter(user_id=notification.user_id, user__is_active=True)

    filters = Q(user__is_active=True)

    if notification.audience_company_id:
        filters &= Q(user__company_id=notification.audience_company_id)

    if notification.audience_resort_id:
        filters &= Q(user__resort_id=notification.audience_resort_id)

    if notification.audience_roles:
        filters &= Q(user__role__in=notification.audience_roles)

    return subscriptions.filter(filters)


def _build_push_payload(notification: Notification) -> dict[str, str]:
    payload = notification.to_payload()
    title = payload.get("title") or notification.display_title or "Notifica"
    body = payload.get("body") or payload.get("message") or notification.message or ""
    url = payload.get("cta_url") or notification.link or "/"

    return {
        "title": title,
        "body": body,
        "category": payload.get("category", notification.category),
        "priority": payload.get("priority", notification.priority),
        "icon": payload.get("icon"),
        "url": url,
        "tag": f"notification-{notification.pk}",
    }


@receiver(post_save, sender=Notification)
def enqueue_push_for_notification(sender, instance: Notification, created: bool, **kwargs) -> None:
    if not created:
        return

    channels = _normalize_channels(getattr(instance, "delivery_channels", None))
    if "push" not in channels:
        return

    payload = _build_push_payload(instance)
    subscriptions = list(_subscriptions_for_notification(instance))

    if not subscriptions:
        logger.debug(
            "Nessuna subscription push attiva per la notifica %s: invio ignorato.",
            instance.pk,
        )
        return

    for subscription in subscriptions:
        try:
            enqueue_notification_push(
                subscription,
                {key: value for key, value in payload.items() if value is not None},
                reason="notification_created",
            )
        except Exception:  # pragma: no cover - failure logged without breaking save flow
            logger.exception(
                "Invio push fallito per la notifica %s e subscription %s.",
                instance.pk,
                subscription.pk,
            )
