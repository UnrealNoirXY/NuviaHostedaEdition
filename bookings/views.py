from django.shortcuts import render, redirect, get_object_or_404
from django.http import Http404, HttpResponse, FileResponse, JsonResponse
from django.urls import reverse
from django.core.cache import cache
from django.core.files.storage import default_storage
from django.conf import settings
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.views.decorators.http import require_POST
from django_fsm import TransitionNotAllowed
import logging
import os
import base64
import json

from .models import (
    Booking,
    CheckInProcess,
    CheckInTransitionEvent,
    Consent,
    DataValidationError,
    Guest,
    GuestDocument,
)
from .token_validation import get_token_error_message, log_failed_token, validate_booking_token
from .forms import GuestFormSet, ConsentForm, OtpForm
from .tasks import (
    send_otp_email_task,
    send_newsletter_confirmation_email_task,
    send_final_confirmation_email_task,
    generate_checkin_pdf_task,
    generate_checkin_qr_task,
)
from communications.email_gateway import dispatch_email_task
from .observability import (
    CHECKIN_EMAIL_COUNTER,
    CHECKIN_OTP_COUNTER,
    CHECKIN_PDF_COUNTER,
    log_checkin_event,
    record_step,
    record_transition,
)
from .ocr import load_image_from_payload, perform_ocr


logger = logging.getLogger(__name__)


def _otp_rate_limited(ip_address, booking_id):
    if not ip_address:
        return False

    cache_key = f"otp-verify:{booking_id}:{ip_address}"
    attempts = cache.get(cache_key, 0)
    if attempts >= CheckInProcess.OTP_RATE_LIMIT_ATTEMPTS_PER_MINUTE:
        return True

    cache.set(cache_key, attempts + 1, timeout=60)
    return False


def _ocr_rate_limited(ip_address, booking_id):
    if not ip_address:
        return False

    cache_key = f"ocr:{booking_id}:{ip_address}"
    attempts = cache.get(cache_key, 0)
    if attempts >= 5:
        return True

    cache.set(cache_key, attempts + 1, timeout=3600)
    return False

def checkin_wizard(request, token):
    """
    Gestisce il flusso di check-in stateful (raccolta dati -> verifica OTP -> firma).
    """
    # --- 1. Verifica del Token e della Prenotazione ---
    booking, reason, token_hash = validate_booking_token(token, status=Booking.Status.PENDING)

    if reason == 'wrong_status':
        log_checkin_event(
            "checkin.token.status_mismatch",
            level=logging.INFO,
            request=request,
            booking=booking,
            token=token,
            booking_status=booking.status,
        )
        if booking.status == Booking.Status.COMPLETED:
            messages.info(request, "Hai già completato il check-in. Qui trovi il riepilogo.")
            return redirect('bookings:checkin_complete', booking_id=booking.id)
        raise Http404(get_token_error_message(reason))

    if not booking:
        log_failed_token(reason, token_hash, request)
        raise Http404(get_token_error_message(reason))

    checkin_process, _ = CheckInProcess.objects.get_or_create(booking=booking)

    # --- 2. Gestione basata sullo stato del processo ---

    if checkin_process.state == CheckInProcess.State.AWAITING_OTP:
        import json
        form = OtpForm(request.POST or None)

        # Prepara i dati per il componente React di validazione documenti
        doc_ids = list(GuestDocument.objects.filter(guest__booking=booking).values_list('id', flat=True))
        context = {
            'form': form,
            'booking': booking,
            'token': token,
            'doc_ids_json': json.dumps(doc_ids),
            'otp_expires_at': checkin_process.otp_expires_at,
            'otp_locked_until': checkin_process.otp_locked_until,
            'otp_attempts_remaining': checkin_process.otp_attempts_remaining,
            'otp_resend_cooldown': CheckInProcess.OTP_RESEND_COOLDOWN_SECONDS,
            'otp_last_sent_at': checkin_process.otp_last_sent_at,
        }

        if request.method == 'POST' and form.is_valid():
            client_ip = request.META.get('REMOTE_ADDR')
            user_agent = request.META.get('HTTP_USER_AGENT')

            if _otp_rate_limited(client_ip, booking.id):
                message = "Troppe richieste di verifica da questo indirizzo IP. Attendi un minuto." \
                    " Continua con calma per evitare il blocco."
                checkin_process.log_otp_attempt(
                    success=False,
                    reason='ip_rate_limit',
                    ip_address=client_ip,
                    user_agent=user_agent,
                    message=message,
                    attempts_remaining=checkin_process.otp_attempts_remaining,
                )
                CHECKIN_OTP_COUNTER.labels(action="verify", status="rate_limited").inc()
                log_checkin_event(
                    "checkin.otp.rate_limited",
                    request=request,
                    booking=booking,
                    token=token,
                    attempts_remaining=checkin_process.otp_attempts_remaining,
                    user_agent=user_agent,
                )
                messages.error(request, message)
                return render(request, 'bookings/checkin_wizard_otp.html', context)

            verification = checkin_process.verify_otp(
                form.cleaned_data['otp_code'],
                ip_address=client_ip,
                user_agent=user_agent,
            )
            verification_status = "success" if verification.get('success') else "failure"
            CHECKIN_OTP_COUNTER.labels(action="verify", status=verification_status).inc()
            log_checkin_event(
                "checkin.otp.verify",
                request=request,
                booking=booking,
                token=token,
                status=verification_status,
                reason=verification.get('reason'),
                attempts_remaining=checkin_process.otp_attempts_remaining,
            )
            if verification.get('success'):
                now = timezone.now()
                signature_meta_for_pdf = {'ip': request.META.get('REMOTE_ADDR', 'N/A'), 'ua': request.META.get('HTTP_USER_AGENT', 'N/A'), 'ts': now}
                qr_content = request.build_absolute_uri(reverse('bookings:checkin_complete', kwargs={'booking_id': booking.id}))
                checkin_process.signature_meta = {'ip': request.META.get('REMOTE_ADDR', 'N/A'), 'ua': request.META.get('HTTP_USER_AGENT', 'N/A'), 'ts': now.isoformat()}
                checkin_process.pdf_status = CheckInProcess.ArtifactStatus.PROCESSING
                checkin_process.qr_status = CheckInProcess.ArtifactStatus.PROCESSING
                checkin_process.save(update_fields=['signature_meta', 'pdf_status', 'qr_status'])

                CHECKIN_PDF_COUNTER.labels(status="queued").inc()
                log_checkin_event(
                    "checkin.pdf.queued",
                    request=request,
                    booking=booking,
                    token=token,
                )

                try:
                    generate_checkin_pdf_task.apply_async(args=[checkin_process.id, signature_meta_for_pdf, request.scheme, request.get_host()])
                except Exception:
                    CHECKIN_PDF_COUNTER.labels(status="fallback_sync").inc()
                    log_checkin_event(
                        "checkin.pdf.dispatch_failed",
                        level=logging.ERROR,
                        request=request,
                        booking=booking,
                        token=token,
                    )
                    logger.exception("Invio del task di generazione PDF fallito, fallback sincrono")
                    result = generate_checkin_pdf_task.apply(args=[checkin_process.id, signature_meta_for_pdf, request.scheme, request.get_host()])
                    logger.info("Esecuzione sincrona generazione PDF completata: %s", result.result)
                    checkin_process.refresh_from_db(fields=['signed_pdf_url', 'signed_pdf_checksum', 'pdf_status'])
                    qr_data = generate_checkin_qr_task(checkin_process.id, qr_content)
                    checkin_process.qr_code_url = qr_data.get('qr_url')
                    checkin_process.save(update_fields=['qr_code_url'])

                try:
                    generate_checkin_qr_task.apply_async(args=[checkin_process.id, qr_content])
                except Exception:
                    logger.exception("Invio del task di generazione QR fallito, fallback sincrono")
                    generate_checkin_qr_task.apply(args=[checkin_process.id, qr_content])

                origin = CheckInTransitionEvent.Origin.WEB

                try:
                    previous_state = checkin_process.state
                    checkin_process.sign(
                        origin=origin,
                        user=request.user,
                        ip_address=request.META.get('REMOTE_ADDR'),
                        metadata=checkin_process.signature_meta,
                    )
                    checkin_process.save()
                    record_transition(
                        checkin_process,
                        previous_state,
                        origin,
                        request=request,
                        token=token,
                    )
                except TransitionNotAllowed as exc:
                    logger.warning(
                        "Transizione sign non permessa", extra={"booking_id": booking.id, "state": checkin_process.state, "ip": request.META.get('REMOTE_ADDR')},
                    )
                    messages.error(request, "Non è stato possibile registrare la firma in questo stato. Riprova dal link di check-in.")
                    return redirect('bookings:dashboard')

                checkin_process.refresh_from_db(fields=['pdf_status', 'signed_pdf_path', 'signed_pdf_checksum', 'signed_pdf_url'])
                if checkin_process.pdf_status == CheckInProcess.ArtifactStatus.READY:
                    try:
                        previous_state = checkin_process.state
                        checkin_process.complete(
                            origin=origin,
                            user=request.user,
                            ip_address=request.META.get('REMOTE_ADDR'),
                            metadata={'doc_sha256': checkin_process.signed_pdf_checksum},
                        )
                        checkin_process.save()
                        record_transition(
                            checkin_process,
                            previous_state,
                            origin,
                            request=request,
                            token=token,
                        )
                        messages.success(request, "Check-in completato con successo!")
                        dispatch_email_task(send_final_confirmation_email_task, booking.id, request.scheme, request.get_host())
                        CHECKIN_EMAIL_COUNTER.labels(type="final_confirmation", status="queued").inc()
                        log_checkin_event(
                            "checkin.email.final_confirmation.dispatched",
                            request=request,
                            booking=booking,
                            token=token,
                        )
                        return redirect('bookings:checkin_complete', booking_id=booking.id)
                    except DataValidationError as exc:
                        logger.warning(
                            "Validazione completamento fallita", extra={"booking_id": booking.id, "state": checkin_process.state, "errors": exc.errors, "ip": request.META.get('REMOTE_ADDR')},
                        )
                        messages.error(request, f"Impossibile completare il check-in: {'; '.join(exc.errors)}")
                    except TransitionNotAllowed as exc:
                        logger.warning(
                            "Transizione complete non permessa", extra={"booking_id": booking.id, "state": checkin_process.state, "ip": request.META.get('REMOTE_ADDR')},
                        )
                        checkin_process.flag_for_review(
                            origin=origin,
                            user=request.user,
                            ip_address=request.META.get('REMOTE_ADDR'),
                            metadata={'reason': 'auto_validation_failed'},
                        )
                        checkin_process.save()
                        record_transition(
                            checkin_process,
                            previous_state,
                            origin,
                            request=request,
                            token=token,
                        )
                        messages.warning(request, "Grazie per aver completato la firma. I tuoi documenti sono in fase di revisione dal nostro staff.")
                        return redirect('bookings:dashboard')
                else:
                    messages.info(request, "Firma registrata. Stiamo generando il PDF firmato, ti avviseremo appena pronto.")
                    return redirect('bookings:dashboard')
            else:
                messages.error(request, verification.get('message', "Codice OTP errato o scaduto. Riprova."))

        with record_step("render_form", request=request, booking=booking, token=token):
            return render(request, 'bookings/checkin_wizard_otp.html', context)

    # STATO: AWAITING_DATA (stato iniziale)
    guest_formset = GuestFormSet(request.POST or None, request.FILES or None)
    consent_form = ConsentForm(request.POST or None)

    if request.method == 'POST':
        try:
            if not guest_formset.is_valid() or not consent_form.is_valid():
                log_checkin_event(
                    "checkin.form.invalid",
                    level=logging.WARNING,
                    request=request,
                    booking=booking,
                    token=token,
                    guest_errors=str(guest_formset.errors),
                    consent_errors=str(consent_form.errors),
                )

            if guest_formset.is_valid() and consent_form.is_valid():
                Guest.objects.filter(booking=booking).delete()
                for form in guest_formset:
                    if form.is_valid() and form.has_changed() and not form.cleaned_data.get('DELETE', False):
                        guest = Guest.objects.create(
                            booking=booking,
                            first_name=form.cleaned_data['first_name'],
                            last_name=form.cleaned_data['last_name'],
                            date_of_birth=form.cleaned_data['date_of_birth'],
                            document_number=form.cleaned_data.get('document_number', ''),
                            document_expiry_date=form.cleaned_data.get('document_expiry_date'),
                        )
                        uploaded_file = form.cleaned_data.get('document_image')
                        if uploaded_file:
                            GuestDocument.objects.create(guest=guest, file=uploaded_file)

                policy_versions = Consent.get_current_policy_versions()
                ip_address = request.META.get('REMOTE_ADDR')
                user_agent = request.META.get('HTTP_USER_AGENT')

                try:
                    Consent.record_consent(
                        booking=booking,
                        consent_type=Consent.ConsentType.TERMS_V1,
                        policy_version=policy_versions.get(Consent.ConsentType.TERMS_V1),
                        source='web_checkin',
                        ip_address=ip_address,
                        user_agent=user_agent,
                    )
                    Consent.record_consent(
                        booking=booking,
                        consent_type=Consent.ConsentType.PRIVACY_V1,
                        policy_version=policy_versions.get(Consent.ConsentType.PRIVACY_V1),
                        source='web_checkin',
                        ip_address=ip_address,
                        user_agent=user_agent,
                    )

                    newsletter_consent = None
                    if consent_form.cleaned_data.get('newsletter_subscription'):
                        newsletter_consent = Consent.record_consent(
                            booking=booking,
                            consent_type=Consent.ConsentType.MARKETING_NEWSLETTER,
                            policy_version=policy_versions.get(Consent.ConsentType.MARKETING_NEWSLETTER),
                            source='web_checkin',
                            ip_address=ip_address,
                            user_agent=user_agent,
                        )
                        dispatch_email_task(send_newsletter_confirmation_email_task, booking.id, request.scheme, request.get_host())
                        messages.info(request, "Grazie per l'iscrizione! Email di conferma inviata.")
                except DataValidationError as exc:
                    messages.error(request, "Errore nella registrazione dei consensi: " + "; ".join(exc.errors))
                    return redirect(request.path)

                raw_otp = checkin_process.issue_otp()
                try:
                    previous_state = checkin_process.state
                    checkin_process.request_otp(
                        origin=CheckInTransitionEvent.Origin.WEB,
                        user=request.user,
                        ip_address=request.META.get('REMOTE_ADDR'),
                    )
                except TransitionNotAllowed:
                    logger.warning(
                        "Transizione request_otp non permessa", extra={"booking_id": booking.id, "state": checkin_process.state, "ip": request.META.get('REMOTE_ADDR')},
                    )
                    log_checkin_event(
                        "checkin.transition.request_otp.blocked",
                        level=logging.WARNING,
                        request=request,
                        booking=booking,
                        token=token,
                        state=checkin_process.state,
                    )
                    messages.error(request, "Non è possibile richiedere un nuovo OTP in questo stato. Aggiorna la pagina o ripeti il check-in.")
                    return redirect(request.path)
                checkin_process.save()
                record_transition(
                    checkin_process,
                    previous_state,
                    CheckInTransitionEvent.Origin.WEB,
                    request=request,
                    token=token,
                )
                dispatch_email_task(send_otp_email_task, booking.id, raw_otp, request.scheme, request.get_host())
                CHECKIN_EMAIL_COUNTER.labels(type="otp", status="queued").inc()
                CHECKIN_OTP_COUNTER.labels(action="issue", status="success").inc()
                log_checkin_event(
                    "checkin.otp.dispatched",
                    request=request,
                    booking=booking,
                    token=token,
                    status="queued",
                )
                messages.info(request, "Abbiamo inviato un codice di verifica al tuo indirizzo email.")
                return redirect(request.path)
        except Exception:
            logger.exception("Errore durante la raccolta dati per il check-in")
            log_checkin_event(
                "checkin.data.error",
                level=logging.ERROR,
                request=request,
                booking=booking,
                token=token,
                alert=True,
            )
            raise


    context = {
        'booking': booking,
        'guest_formset': guest_formset,
        'consent_form': consent_form,
        'token': token,
    }
    with record_step("render_form", request=request, booking=booking, token=token):
        return render(request, 'bookings/checkin_wizard_data.html', context)


@require_POST
def checkin_ocr_view(request):
    payload = {}
    if request.content_type and 'application/json' in request.content_type:
        try:
            payload = json.loads(request.body.decode() or "{}")
        except ValueError:
            payload = {}
    else:
        payload = request.POST

    token = payload.get('token') or request.headers.get('X-Booking-Token')
    if not token:
        return JsonResponse({'error': 'Token mancante.'}, status=400)

    booking, reason, token_hash = validate_booking_token(token, status=Booking.Status.PENDING)
    if not booking or reason:
        log_failed_token(reason, token_hash, request)
        return JsonResponse({'error': get_token_error_message(reason)}, status=404)

    ip_address = request.META.get('REMOTE_ADDR')
    if _ocr_rate_limited(ip_address, booking.id):
        log_checkin_event(
            "checkin.ocr.rate_limited",
            request=request,
            booking=booking,
            token=token,
            metadata={"ip": ip_address},
        )
        return JsonResponse({'error': 'Troppe richieste OCR da questo IP. Attendi qualche minuto e riprova.'}, status=429)

    try:
        image = load_image_from_payload(image_file=request.FILES.get('image'), image_base64=payload.get('image_base64'))
    except ValueError as exc:
        return JsonResponse({'error': str(exc)}, status=400)

    try:
        result = perform_ocr(image)
    except ValueError as exc:
        return JsonResponse({'error': str(exc)}, status=400)
    except Exception:
        logger.exception("Errore durante l'elaborazione OCR lato backend")
        return JsonResponse({'error': 'Errore durante l\'elaborazione dell\'immagine. Riprova o carica un file diverso.'}, status=500)

    masked_fields = {k: (v[:3] + "***" if v else "") for k, v in result.get('fields', {}).items()}
    log_checkin_event(
        "checkin.ocr.completed",
        request=request,
        booking=booking,
        token=token,
        metadata={"confidence": result.get('confidence'), "fields": masked_fields},
    )

    return JsonResponse({
        'fields': result.get('fields', {}),
        'confidence': result.get('confidence', 0),
        'source': 'backend',
    })


@require_POST
def checkin_client_log_view(request):
    payload = {}
    if request.content_type and 'application/json' in request.content_type:
        try:
            payload = json.loads(request.body.decode() or "{}")
        except ValueError:
            payload = {}
    else:
        payload = request.POST

    token = payload.get('token') or request.headers.get('X-Booking-Token')
    if not token:
        return JsonResponse({'error': 'Token mancante.'}, status=400)

    booking, reason, token_hash = validate_booking_token(token, status=Booking.Status.PENDING)
    if not booking or reason:
        log_failed_token(reason, token_hash, request)
        return JsonResponse({'error': get_token_error_message(reason)}, status=404)

    level_name = str(payload.get('level') or 'info').lower()
    level = {
        'error': logging.ERROR,
        'warn': logging.WARNING,
        'warning': logging.WARNING,
        'info': logging.INFO,
    }.get(level_name, logging.INFO)

    message = payload.get('message') or 'Evento client non specificato'
    context = payload.get('context') or {}

    log_checkin_event(
        "checkin.client.log",
        level=level,
        request=request,
        booking=booking,
        token=token,
        client_message=message,
        client_context=context,
    )

    return JsonResponse({'status': 'ok'})


@login_required
@permission_required("bookings.view_guestdocument", raise_exception=True)
def serve_doc(request, pk):
    """
    Serve in modo sicuro i file dei documenti degli ospiti, verificando i permessi.
    """
    doc = get_object_or_404(GuestDocument, pk=pk)
    return FileResponse(doc.file.open("rb"), as_attachment=True, filename=os.path.basename(doc.file.name))

# --- Viste di supporto e GDPR ---

def checkin_complete_view(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, status=Booking.Status.COMPLETED)
    checkin_process = get_object_or_404(CheckInProcess, booking=booking)
    qr_code_base64 = None
    if checkin_process.qr_status == CheckInProcess.ArtifactStatus.READY and checkin_process.qr_code_path and default_storage.exists(checkin_process.qr_code_path):
        with default_storage.open(checkin_process.qr_code_path, 'rb') as f:
            qr_code_base64 = base64.b64encode(f.read()).decode('utf-8')

    context = {'booking': booking, 'qr_code_base64': qr_code_base64, 'qr_status': checkin_process.qr_status}
    return render(request, 'bookings/checkin_complete.html', context)

@login_required
def booking_dashboard_view(request):
    return render(request, 'bookings/react_dashboard_root.html')

def download_pdf_view(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)
    checkin_process = get_object_or_404(CheckInProcess, booking=booking)
    if not checkin_process.signed_pdf_path:
        raise Http404("PDF non trovato.")
    if default_storage.exists(checkin_process.signed_pdf_path):
        with default_storage.open(checkin_process.signed_pdf_path, 'rb') as f:
            response = HttpResponse(f.read(), content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="checkin_summary_{booking.id}.pdf"'
            return response
    raise Http404("File PDF non trovato sul server.")


@login_required
def artifact_status_view(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)
    checkin_process = get_object_or_404(CheckInProcess, booking=booking)
    data = {
        'pdf_status': checkin_process.pdf_status,
        'qr_status': checkin_process.qr_status,
        'signed_pdf_url': checkin_process.signed_pdf_url,
        'qr_code_url': checkin_process.qr_code_url,
        'signed_pdf_checksum': checkin_process.signed_pdf_checksum,
    }
    return JsonResponse(data)

def data_export_view(request, token):
    from django.http import JsonResponse
    booking, reason, token_hash = validate_booking_token(token)
    if not booking:
        log_failed_token(reason, token_hash, request)
        return JsonResponse({'error': get_token_error_message(reason)}, status=404)
    data = {'message': 'Richiesta di esportazione dati ricevuta.', 'booking_id': booking.id}
    return JsonResponse(data)

def data_erasure_view(request, token):
    from django.http import JsonResponse
    booking, reason, token_hash = validate_booking_token(token)
    if not booking:
        log_failed_token(reason, token_hash, request)
        return JsonResponse({'error': get_token_error_message(reason)}, status=404)
    booking.guest_name, booking.guest_email = "Anonymized", "anonymized@example.com"
    booking.save()
    Guest.objects.filter(booking=booking).update(first_name="Anonymized", last_name="Anonymized")
    data = {'message': 'Richiesta di cancellazione dati ricevuta ed elaborata.', 'booking_id': booking.id}
    return JsonResponse(data)