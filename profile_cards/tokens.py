import secrets
from datetime import timedelta

from django.utils import timezone

from .models import ProfileCardPublicToken, ProfileCardSettings


def issue_public_token(card, days=None):
    settings = ProfileCardSettings.get_solo()
    effective_days = days if days is not None else settings.default_token_days

    active = (
        ProfileCardPublicToken.objects.filter(card=card, revoked_at__isnull=True, expires_at__gt=timezone.now())
        .order_by("-created_at")
        .first()
    )
    if active:
        return active
    return ProfileCardPublicToken.objects.create(
        card=card,
        token=secrets.token_urlsafe(24),
        expires_at=timezone.now() + timedelta(days=effective_days),
    )
