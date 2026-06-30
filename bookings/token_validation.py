import logging
from typing import Optional

from django.utils import timezone

from .models import Booking

logger = logging.getLogger("bookings.token")

TOKEN_ERROR_MESSAGES = {
    "not_found": "Token non valido o prenotazione non trovata.",
    "expired": "Il link di accesso è scaduto. Richiedi un nuovo link.",
    "revoked": "Il link non è più valido. Contatta l'assistenza per un nuovo accesso.",
    "locked": "Il link è stato bloccato per motivi di sicurezza. Richiedi un nuovo accesso.",
    "wrong_status": "Il check-in per questa prenotazione non è più disponibile.",
}


def validate_booking_token(raw_token: str, status: Optional[str] = None):
    booking, reason, token_hash = Booking.validate_access_token(raw_token, status=status)
    if reason:
        return booking, reason, token_hash
    return booking, None, token_hash


def log_failed_token(reason: str, token_hash: str, request=None):
    log_payload = {
        "event": "booking_token_validation_failed",
        "reason": reason,
        "token_hash": token_hash,
    }
    if request is not None:
        log_payload.update(
            {
                "path": getattr(request, "path", None),
                "ip": request.META.get("REMOTE_ADDR"),
                "user_agent": request.META.get("HTTP_USER_AGENT"),
                "ts": timezone.now().isoformat(),
            }
        )
    logger.warning("Access token validation failed", extra=log_payload)


def get_token_error_message(reason: str) -> str:
    return TOKEN_ERROR_MESSAGES.get(reason, TOKEN_ERROR_MESSAGES["not_found"])
