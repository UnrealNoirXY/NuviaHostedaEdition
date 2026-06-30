import logging
import time
from contextlib import contextmanager
from typing import Any, Dict, Optional

from prometheus_client import Counter, Histogram


logger = logging.getLogger("bookings.checkin")


CHECKIN_STEP_LATENCY = Histogram(
    "checkin_step_duration_seconds",
    "Durata dei passaggi principali del check-in",
    labelnames=["step"],
)

CHECKIN_STATE_TRANSITIONS = Counter(
    "checkin_state_transition_total",
    "Conteggio delle transizioni di stato del check-in",
    labelnames=["from_state", "to_state", "origin"],
)

CHECKIN_EMAIL_COUNTER = Counter(
    "checkin_email_total",
    "Invii email nel flusso di check-in",
    labelnames=["type", "status"],
)

CHECKIN_PDF_COUNTER = Counter(
    "checkin_pdf_generation_total",
    "Esiti della generazione PDF di riepilogo",
    labelnames=["status"],
)

CHECKIN_OTP_COUNTER = Counter(
    "checkin_otp_total",
    "Flusso OTP (invio/verifica)",
    labelnames=["action", "status"],
)


def _mask_token(token: Optional[str]) -> Optional[str]:
    if not token:
        return None
    if len(token) <= 8:
        return "***"
    return f"{token[:4]}***{token[-4:]}"


def correlation_fields(
    request=None, booking=None, token: Optional[str] = None, **extra
) -> Dict[str, Any]:
    user = getattr(request, "user", None) if request is not None else None
    ip_address = request.META.get("REMOTE_ADDR") if request is not None else None
    correlation_id_parts = []
    if booking:
        correlation_id_parts.append(f"booking:{booking.id}")
    masked_token = _mask_token(token)
    if masked_token:
        correlation_id_parts.append(f"token:{masked_token}")
    if ip_address:
        correlation_id_parts.append(f"ip:{ip_address}")

    correlation_id = "|".join(correlation_id_parts) if correlation_id_parts else None

    payload = {
        "correlation_id": correlation_id,
        "booking_id": getattr(booking, "id", None),
        "masked_token": masked_token,
        "user_id": getattr(user, "id", None) if getattr(user, "is_authenticated", False) else None,
        "ip_address": ip_address,
        **extra,
    }
    return {k: v for k, v in payload.items() if v is not None}


def log_checkin_event(
    message: str,
    *,
    level: int = logging.INFO,
    request=None,
    booking=None,
    token: Optional[str] = None,
    **fields,
) -> None:
    extra = correlation_fields(request=request, booking=booking, token=token, **fields)
    logger.log(level, message, extra=extra)


def record_transition(process, previous_state: str, origin: str, *, request=None, token=None):
    CHECKIN_STATE_TRANSITIONS.labels(
        from_state=previous_state,
        to_state=process.state,
        origin=origin,
    ).inc()
    log_checkin_event(
        "checkin.transition",
        request=request,
        booking=process.booking,
        token=token,
        previous_state=previous_state,
        current_state=process.state,
        origin=origin,
    )


@contextmanager
def record_step(step: str, *, request=None, booking=None, token=None):
    start = time.perf_counter()
    status = "ok"
    try:
        yield
    except Exception:
        status = "error"
        raise
    finally:
        duration = time.perf_counter() - start
        CHECKIN_STEP_LATENCY.labels(step=step).observe(duration)
        log_checkin_event(
            "checkin.step",
            request=request,
            booking=booking,
            token=token,
            step=step,
            status=status,
            duration_ms=round(duration * 1000, 2),
        )
