from celery import shared_task
import logging
from django.conf import settings
from django.utils import timezone
from PIL import Image
import pytesseract
import pandas as pd
import io

import qrcode

from bookings.models import Booking, CheckInProcess, GuestDocument
from communications.email_gateway import EmailGateway, log_email_outcome
from communications.models import EmailLog
from bookings.storage_utils import save_bytes_with_retries
from bookings.utils import generate_checkin_pdf
from bookings.observability import (
    CHECKIN_EMAIL_COUNTER,
    CHECKIN_PDF_COUNTER,
    log_checkin_event,
    record_step,
)

logger = logging.getLogger(__name__)
email_gateway = EmailGateway()

@shared_task
def scan_and_ocr_document(doc_id):
    """
    Task asincrono per eseguire la scansione AV e l'analisi OCR di un documento
    utilizzando Tesseract.
    """
    logger.info(f"Avvio scansione OCR reale per il documento {doc_id}...")
    try:
        doc = GuestDocument.objects.get(id=doc_id)

        if not doc.file:
            logger.error(f"Documento {doc_id} non ha un file associato.")
            return

        # Simula scansione antivirus (in produzione, usare un servizio come ClamAV)
        doc.scan_result = "clean"
        logger.info(f"Documento {doc_id}: Scansione AV simulata -> {doc.scan_result}")

        try:
            # Apri l'immagine e processala con Tesseract
            image = Image.open(io.BytesIO(doc.file.read()))

            # Usa image_to_data per ottenere un DataFrame con i dettagli
            ocr_data = pytesseract.image_to_data(
                image,
                output_type=pytesseract.Output.DATAFRAME,
                lang='ita'  # Specifica la lingua per una maggiore accuratezza
            )

            # Filtra i dati per parole con una confidenza valida
            ocr_data = ocr_data[ocr_data.conf > -1]

            # Calcola la confidenza media ponderata sul numero di caratteri
            if not ocr_data.empty:
                total_conf = (ocr_data['conf'] * ocr_data['text'].str.len()).sum()
                total_chars = ocr_data['text'].str.len().sum()
                average_confidence = total_conf / total_chars if total_chars > 0 else 0
                doc.ocr_confidence = average_confidence / 100.0  # Normalizza a 0-1
            else:
                doc.ocr_confidence = 0.0

            logger.info(f"Documento {doc_id}: Analisi OCR reale -> Confidenza {doc.ocr_confidence:.2f}")

        except Exception as ocr_error:
            logger.error(f"Errore durante l'elaborazione OCR per il documento {doc_id}: {ocr_error}", exc_info=True)
            doc.scan_result = "error_ocr"
            doc.ocr_confidence = 0.0

        doc.scanned_at = timezone.now()
        doc.save(update_fields=["scan_result", "ocr_confidence", "scanned_at"])
        logger.info(f"Documento {doc_id} processato e salvato con successo.")

    except GuestDocument.DoesNotExist:
        logger.error(f"ERRORE CRITICO: Documento con ID {doc_id} non trovato durante la scansione.")
    except Exception as e:
        logger.error(f"ERRORE imprevisto durante la scansione del documento {doc_id}: {e}", exc_info=True)


# --- Altri task esistenti ---


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_jitter=True, retry_kwargs={'max_retries': 3})
def generate_checkin_pdf_task(self, checkin_process_id, signature_meta, scheme, host):
    try:
        process = CheckInProcess.objects.select_related("booking").get(id=checkin_process_id)
    except CheckInProcess.DoesNotExist as exc:  # pragma: no cover - validazione input
        logger.error("Processo di check-in %s non trovato per la generazione PDF", checkin_process_id)
        CHECKIN_PDF_COUNTER.labels(status="failed").inc()
        log_checkin_event(
            "checkin.pdf.missing_process",
            level=logging.ERROR,
            booking=None,
            token=None,
            alert=True,
            process_id=checkin_process_id,
        )
        raise

    booking = process.booking
    process.pdf_status = CheckInProcess.ArtifactStatus.PROCESSING
    process.save(update_fields=["pdf_status"])

    with record_step("generate_pdf", booking=booking):
        pdf_content, pdf_hash = generate_checkin_pdf(booking, signature_meta)
        pdf_filename = f"signed_documents/checkin_summary_{booking.id}_{pdf_hash[:10]}.pdf"

        try:
            saved_path, signed_url = save_bytes_with_retries(pdf_filename, pdf_content)
        except Exception as exc:  # pragma: no cover - affidato al retry
            process.pdf_status = CheckInProcess.ArtifactStatus.FAILED
            process.save(update_fields=["pdf_status"])
            CHECKIN_PDF_COUNTER.labels(status="failed").inc()
            log_checkin_event(
                "checkin.pdf.save_failed",
                level=logging.ERROR,
                booking=booking,
                token=None,
                alert=True,
                error=str(exc),
            )
            logger.error("Salvataggio PDF fallito per il booking %s: %s", booking.id, exc)
            raise

        merged_signature_meta = signature_meta.copy()
        merged_signature_meta["doc_sha256"] = pdf_hash

        process.signed_pdf_url = signed_url
        process.signed_pdf_path = saved_path
        process.signed_pdf_checksum = pdf_hash
        process.signature_meta = merged_signature_meta
        process.pdf_status = CheckInProcess.ArtifactStatus.READY
        process.save(
            update_fields=[
                "signed_pdf_url",
                "signed_pdf_path",
                "signed_pdf_checksum",
                "signature_meta",
                "pdf_status",
            ]
        )
        CHECKIN_PDF_COUNTER.labels(status="completed").inc()
        log_checkin_event(
            "checkin.pdf.generated",
            booking=booking,
            token=None,
            checksum=pdf_hash,
            signed_url=signed_url,
        )

    return {"pdf_url": signed_url, "checksum": pdf_hash}


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_jitter=True, retry_kwargs={'max_retries': 3})
def generate_checkin_qr_task(self, checkin_process_id, base_url):
    try:
        process = CheckInProcess.objects.select_related("booking").get(id=checkin_process_id)
    except CheckInProcess.DoesNotExist as exc:  # pragma: no cover - validazione input
        logger.error("Processo di check-in %s non trovato per la generazione del QR", checkin_process_id)
        raise

    process.qr_status = CheckInProcess.ArtifactStatus.PROCESSING
    process.save(update_fields=["qr_status"])

    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(base_url)
    qr.make(fit=True)
    img = qr.make_image(fill='black', back_color='white')
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)

    qr_filename = f"qr_codes/checkin_{process.booking_id}.png"
    try:
        saved_path, signed_url = save_bytes_with_retries(qr_filename, buffer.read())
    except Exception as exc:  # pragma: no cover - affidato al retry
        process.qr_status = CheckInProcess.ArtifactStatus.FAILED
        process.save(update_fields=["qr_status"])
        logger.error("Salvataggio QR fallito per il booking %s: %s", process.booking_id, exc)
        raise

    process.qr_code_path = saved_path
    process.qr_code_url = signed_url
    process.qr_status = CheckInProcess.ArtifactStatus.READY
    process.save(update_fields=["qr_code_path", "qr_code_url", "qr_status"])

    return {"qr_url": signed_url}

def _log_success(task_name, booking, recipient, link_used="", payload=None, task_id=None):
    log_email_outcome(
        task_name=task_name,
        recipient=recipient,
        status=EmailLog.Status.SUCCESS,
        booking=booking,
        link_used=link_used,
        celery_task_id=task_id or "",
        payload=payload,
    )


def _log_failure(task_name, booking, recipient, error, link_used="", payload=None, task_id=None):
    log_email_outcome(
        task_name=task_name,
        recipient=recipient,
        status=EmailLog.Status.FAILED,
        booking=booking,
        link_used=link_used,
        celery_task_id=task_id or "",
        payload=payload,
        error_message=str(error),
    )


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_jitter=True, retry_kwargs={'max_retries': 5})
def send_invitation_email_task(self, booking_id, scheme, host):
    task_name = 'send_invitation_email_task'
    try:
        booking = Booking.objects.get(id=booking_id)
        from bookings.utils import send_checkin_invitation_email
        link_used = send_checkin_invitation_email(booking, scheme, host)
        _log_success(task_name, booking, booking.guest_email, link_used=link_used, task_id=self.request.id)
        logger.info(f"Email di invito inviata con successo per la prenotazione {booking_id}.")
        return link_used
    except Booking.DoesNotExist as exc:
        logger.error(f"ERRORE: Prenotazione con ID {booking_id} non trovata.")
        _log_failure(task_name, None, "", exc)
        raise
    except Exception as e:
        logger.error(f"ERRORE nell'invio dell'email di invito per la prenotazione {booking_id}: {e}", exc_info=True)
        _log_failure(task_name, booking if 'booking' in locals() else None, booking.guest_email if 'booking' in locals() else "", e, task_id=self.request.id)
        raise


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_jitter=True, retry_kwargs={'max_retries': 5})
def send_otp_email_task(self, booking_id, otp_code, scheme, host):
    task_name = 'send_otp_email_task'
    try:
        booking = Booking.objects.get(id=booking_id)
        from bookings.utils import send_otp_email
        with record_step("send_otp_email", booking=booking):
            send_otp_email(booking, otp_code, scheme, host)
        CHECKIN_EMAIL_COUNTER.labels(type="otp", status="sent").inc()
        log_checkin_event(
            "checkin.email.otp.sent",
            booking=booking,
            token=None,
            status="sent",
        )
        _log_success(task_name, booking, booking.guest_email, payload={"otp": "masked"}, task_id=self.request.id)
        logger.info(f"Email OTP inviata con successo per la prenotazione {booking_id}.")
    except Booking.DoesNotExist as exc:
        logger.error(f"ERRORE: Prenotazione con ID {booking_id} non trovata.")
        CHECKIN_EMAIL_COUNTER.labels(type="otp", status="failed").inc()
        log_checkin_event(
            "checkin.email.otp.failed",
            level=logging.ERROR,
            booking=None,
            token=None,
            alert=True,
            booking_id=booking_id,
            reason="not_found",
        )
        _log_failure(task_name, None, "", exc, payload={"otp": "masked"})
        raise
    except Exception as e:
        logger.error(f"ERRORE nell'invio dell'email OTP per la prenotazione {booking_id}: {e}", exc_info=True)
        CHECKIN_EMAIL_COUNTER.labels(type="otp", status="failed").inc()
        log_checkin_event(
            "checkin.email.otp.failed",
            level=logging.ERROR,
            booking=booking if 'booking' in locals() else None,
            token=None,
            alert=True,
            error=str(e),
        )
        _log_failure(task_name, booking if 'booking' in locals() else None, booking.guest_email if 'booking' in locals() else "", e, payload={"otp": "masked"}, task_id=self.request.id)
        raise


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_jitter=True, retry_kwargs={'max_retries': 5})
def send_final_confirmation_email_task(self, booking_id, scheme, host):
    task_name = 'send_final_confirmation_email_task'
    try:
        booking = Booking.objects.get(id=booking_id)
        from bookings.utils import send_final_confirmation_email
        with record_step("send_final_email", booking=booking):
            send_final_confirmation_email(booking, scheme, host)
        CHECKIN_EMAIL_COUNTER.labels(type="final_confirmation", status="sent").inc()
        log_checkin_event(
            "checkin.email.final_confirmation.sent",
            booking=booking,
            token=None,
            status="sent",
        )
        _log_success(task_name, booking, booking.guest_email, task_id=self.request.id)
        logger.info(f"Email di conferma finale inviata per la prenotazione {booking_id}.")
        return "final_confirmation_sent"
    except Booking.DoesNotExist as exc:
        logger.error(f"ERRORE: Prenotazione con ID {booking_id} non trovata.")
        CHECKIN_EMAIL_COUNTER.labels(type="final_confirmation", status="failed").inc()
        log_checkin_event(
            "checkin.email.final_confirmation.failed",
            level=logging.ERROR,
            booking=None,
            token=None,
            alert=True,
            booking_id=booking_id,
            reason="not_found",
        )
        _log_failure(task_name, None, "", exc)
        raise
    except Exception as e:
        logger.error(f"ERRORE nell'invio dell'email di conferma finale per la prenotazione {booking_id}: {e}", exc_info=True)
        CHECKIN_EMAIL_COUNTER.labels(type="final_confirmation", status="failed").inc()
        log_checkin_event(
            "checkin.email.final_confirmation.failed",
            level=logging.ERROR,
            booking=booking if 'booking' in locals() else None,
            token=None,
            alert=True,
            error=str(e),
        )
        _log_failure(task_name, booking if 'booking' in locals() else None, booking.guest_email if 'booking' in locals() else "", e, task_id=self.request.id)
        raise


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_jitter=True, retry_kwargs={'max_retries': 5})
def send_newsletter_confirmation_email_task(self, booking_id, scheme, host):
    task_name = 'send_newsletter_confirmation_email_task'
    try:
        booking = Booking.objects.get(id=booking_id)
        from bookings.utils import send_newsletter_confirmation_email
        send_newsletter_confirmation_email(booking, scheme, host)
        _log_success(task_name, booking, booking.guest_email, task_id=self.request.id)
        logger.info(f"Email di conferma newsletter inviata per la prenotazione {booking_id}.")
        return "newsletter_confirmation_sent"
    except Booking.DoesNotExist as exc:
        logger.error(f"ERRORE: Prenotazione con ID {booking_id} non trovata.")
        _log_failure(task_name, None, "", exc)
        raise
    except Exception as e:
        logger.error(f"ERRORE nell'invio dell'email di conferma newsletter per la prenotazione {booking_id}: {e}", exc_info=True)
        _log_failure(task_name, booking if 'booking' in locals() else None, booking.guest_email if 'booking' in locals() else "", e, task_id=self.request.id)
        raise


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_jitter=True, retry_kwargs={'max_retries': 5})
def send_booking_creation_email_task(self, booking_id, scheme, host):
    """Task asincrono per inviare l'email di notifica di creazione prenotazione."""
    task_name = 'send_booking_creation_email_task'
    try:
        booking = Booking.objects.get(id=booking_id)
        from bookings.utils import send_booking_creation_email
        link_used = send_booking_creation_email(booking, scheme, host)
        _log_success(task_name, booking, booking.guest_email, link_used=link_used, task_id=self.request.id)
        logger.info(f"Email di notifica creazione inviata per la prenotazione {booking_id}.")
        return link_used
    except Booking.DoesNotExist as exc:
        logger.error(f"ERRORE: Prenotazione con ID {booking_id} non trovata.")
        _log_failure(task_name, None, "", exc)
        raise
    except Exception as e:
        logger.error(f"ERRORE nell'invio dell'email di creazione per la prenotazione {booking_id}: {e}", exc_info=True)
        _log_failure(task_name, booking if 'booking' in locals() else None, booking.guest_email if 'booking' in locals() else "", e, link_used=link_used if 'link_used' in locals() else "", task_id=self.request.id)
        raise


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_jitter=True, retry_kwargs={'max_retries': 5})
def send_booking_update_email_task(self, booking_id, scheme, host):
    """Task asincrono per inviare l'email di notifica di modifica prenotazione."""
    task_name = 'send_booking_update_email_task'
    try:
        booking = Booking.objects.get(id=booking_id)
        from bookings.utils import send_booking_update_email
        link_used = send_booking_update_email(booking, scheme, host)
        _log_success(task_name, booking, booking.guest_email, link_used=link_used, task_id=self.request.id)
        logger.info(f"Email di notifica modifica inviata per la prenotazione {booking_id}.")
        return link_used
    except Booking.DoesNotExist as exc:
        logger.error(f"ERRORE: Prenotazione con ID {booking_id} non trovata.")
        _log_failure(task_name, None, "", exc)
        raise
    except Exception as e:
        logger.error(f"ERRORE nell'invio dell'email di modifica per la prenotazione {booking_id}: {e}", exc_info=True)
        _log_failure(task_name, booking if 'booking' in locals() else None, booking.guest_email if 'booking' in locals() else "", e, link_used=link_used if 'link_used' in locals() else "", task_id=self.request.id)
        raise


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_jitter=True, retry_kwargs={'max_retries': 5})
def send_booking_deletion_email_task(self, booking_details):
    """Task asincrono per inviare l'email di notifica di cancellazione prenotazione."""
    task_name = 'send_booking_deletion_email_task'
    recipient = booking_details.get('guest_email', '')
    try:
        from bookings.utils import send_booking_deletion_email
        send_booking_deletion_email(booking_details)
        _log_success(task_name, None, recipient, payload={"booking_engine_id": booking_details.get('booking_engine_id')}, task_id=self.request.id)
        logger.info(f"Email di notifica cancellazione inviata per la prenotazione (dettagli: {booking_details.get('guest_name')}).")
        return "booking_deletion_sent"
    except Exception as e:
        logger.error(f"ERRORE nell'invio dell'email di cancellazione: {e}", exc_info=True)
        _log_failure(task_name, None, recipient, e, payload={"booking_engine_id": booking_details.get('booking_engine_id')}, task_id=self.request.id)
        raise