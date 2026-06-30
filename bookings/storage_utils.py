import time
import logging
from django.core import signing
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

logger = logging.getLogger(__name__)


def _build_signed_url(saved_path: str, expiry_seconds: int = 3600) -> str:
    base_url = default_storage.url(saved_path)
    token = signing.TimestampSigner().sign(saved_path)
    return f"{base_url}?token={token}&expires={expiry_seconds}"


def save_bytes_with_retries(file_path: str, content_bytes: bytes, *, max_retries: int = 3, sleep_seconds: float = 0.5):
    last_error = None
    saved_path = None
    for attempt in range(1, max_retries + 1):
        try:
            saved_path = default_storage.save(file_path, ContentFile(content_bytes))
            signed_url = _build_signed_url(saved_path)
            return saved_path, signed_url
        except Exception as exc:  # pragma: no cover - defensive logging
            last_error = exc
            logger.warning(
                "Errore al salvataggio dell'artefatto %s (tentativo %s/%s): %s",
                file_path,
                attempt,
                max_retries,
                exc,
            )
            if saved_path:
                try:
                    default_storage.delete(saved_path)
                except Exception:
                    logger.warning("Impossibile eliminare il file orfano %s", saved_path)
            if attempt < max_retries:
                time.sleep(sleep_seconds * attempt)
    if last_error:
        raise last_error
    raise RuntimeError("Impossibile salvare il file richiesto")
