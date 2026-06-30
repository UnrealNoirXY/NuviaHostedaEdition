from datetime import timedelta

from django.db.models import Count
from django.utils import timezone

from .models import ProfileCard, ProfileCardDelivery, ProfileCardEvent, ProfileCardPublicToken


def _pct(numerator, denominator):
    if not denominator:
        return 0.0
    return round((numerator / denominator) * 100, 2)


def get_kpi_summary(days=30):
    since = timezone.now() - timedelta(days=days)

    total_events = ProfileCardEvent.objects.filter(created_at__gte=since)
    grouped = {item["event_type"]: item["count"] for item in total_events.values("event_type").annotate(count=Count("id"))}

    opens = grouped.get(ProfileCardEvent.EVENT_OPEN, 0)
    shares = grouped.get(ProfileCardEvent.EVENT_SHARE, 0)
    wallet_adds = grouped.get(ProfileCardEvent.EVENT_ADD_WALLET, 0)
    vcard_downloads = grouped.get(ProfileCardEvent.EVENT_VCARD, 0)

    deliveries = ProfileCardDelivery.objects.filter(created_at__gte=since)
    delivery_total = deliveries.count()
    delivery_success = deliveries.filter(status=ProfileCardDelivery.STATUS_SENT).count()
    email_bounces = deliveries.filter(status=ProfileCardDelivery.STATUS_BOUNCED).count()
    delivery_failed = deliveries.filter(status__in=[ProfileCardDelivery.STATUS_FAILED, ProfileCardDelivery.STATUS_BOUNCED]).count()

    active_tokens = ProfileCardPublicToken.objects.filter(created_at__gte=since).count()
    cards_created = ProfileCard.objects.filter(created_at__gte=since).count()

    return {
        "window_days": days,
        "opens": opens,
        "shares": shares,
        "wallet_adds": wallet_adds,
        "vcard_downloads": vcard_downloads,
        "email_bounces": email_bounces,
        "delivery_total": delivery_total,
        "delivery_success": delivery_success,
        "delivery_failed": delivery_failed,
        # Phase 11 KPI rates
        "open_rate": _pct(opens, active_tokens),
        "share_rate": _pct(shares, opens),
        "vcard_rate": _pct(vcard_downloads, opens),
        "wallet_add_rate": _pct(wallet_adds, opens),
        "email_success_rate": _pct(delivery_success, delivery_total),
        "avg_card_creation_per_day": round(cards_created / max(days, 1), 2),
    }
