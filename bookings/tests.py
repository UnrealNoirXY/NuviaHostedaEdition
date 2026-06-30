from django.test import TestCase, override_settings
from django.utils import timezone
from django.core import mail, signing
from django.core.management import call_command
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from unittest.mock import patch
import datetime
import io
import base64
import json

from bookings.models import (
    Booking,
    CheckInProcess,
    CheckInTransitionEvent,
    Consent,
    DataValidationError,
    Guest,
    GuestDocument,
)
from resort.models import Resort
from bookings.utils import generate_checkin_pdf
from bookings.tasks import (
    scan_and_ocr_document,
    send_otp_email_task,
    send_booking_creation_email_task,
)
from django_fsm import TransitionNotAllowed
from communications.email_gateway import dispatch_email_task
from communications.models import EmailLog
from core.models import PlatformSettings
from django.urls import reverse
from django.utils.crypto import salted_hmac

def create_test_image():
    """Crea un'immagine PNG 1x1 valida per i test."""
    # Questo è il payload di un'immagine PNG 1x1 trasparente
    png_data = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
    )
    return SimpleUploadedFile("test.png", png_data, content_type="image/png")

class BookingModelTests(TestCase):

    def setUp(self):
        """Crea un resort e una prenotazione di base per i test."""
        self.resort = Resort.objects.create(name="Test Resort")
        self.booking = Booking.objects.create(
            guest_name="Test User",
            guest_email="test@example.com",
            check_in_date=timezone.now().date(),
            check_out_date=timezone.now().date() + datetime.timedelta(days=5),
            resort=self.resort
        )

    def test_issue_and_verify_access_token(self):
        """Verifica che un token possa essere generato e validato correttamente."""
        raw_token = self.booking.issue_access_token()
        self.assertIsNotNone(raw_token)
        self.assertTrue(self.booking.verify_access_token(raw_token))

    def test_verify_invalid_token(self):
        """Verifica che un token non corretto non venga validato."""
        self.booking.issue_access_token()
        self.assertFalse(self.booking.verify_access_token("invalidtoken"))


@override_settings(CELERY_TASK_ALWAYS_EAGER=True, EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class ConsentPolicyTests(TestCase):

    def setUp(self):
        self.resort = Resort.objects.create(name="Policy Resort")
        self.booking = Booking.objects.create(
            guest_name="Policy User",
            guest_email="policy@example.com",
            check_in_date=timezone.now().date(),
            check_out_date=timezone.now().date() + datetime.timedelta(days=2),
            resort=self.resort,
        )

    def test_record_consent_supersedes_previous_and_tracks_metadata(self):
        first = Consent.record_consent(
            booking=self.booking,
            consent_type=Consent.ConsentType.TERMS_V1,
            policy_version="v1.0",
            source="web_checkin",
            ip_address="127.0.0.1",
            user_agent="TestAgent",
        )
        second = Consent.record_consent(
            booking=self.booking,
            consent_type=Consent.ConsentType.TERMS_V1,
            policy_version="v2.0",
            source="web_checkin",
            ip_address="127.0.0.1",
            user_agent="TestAgent",
        )

        first.refresh_from_db()
        self.assertEqual(first.status, Consent.Status.SUPERSEDED)
        self.assertIsNotNone(first.superseded_at)
        self.assertEqual(second.status, Consent.Status.CURRENT)
        self.assertEqual(second.ip_address, "127.0.0.1")
        self.assertEqual(second.user_agent, "TestAgent")
        self.assertEqual(second.policy_version, "v2.0")

    def test_policy_versions_read_from_platform_settings(self):
        settings = PlatformSettings.load()
        settings.terms_policy_version = "v9.9"
        settings.save()

        consent = Consent.record_consent(
            booking=self.booking,
            consent_type=Consent.ConsentType.TERMS_V1,
            policy_version=Consent.get_current_policy_versions()[Consent.ConsentType.TERMS_V1],
            source="web_checkin",
        )

        self.assertEqual(consent.policy_version, "v9.9")

    def test_outdated_consent_blocks_completion(self):
        settings = PlatformSettings.load()
        settings.terms_policy_version = "v1.0"
        settings.privacy_policy_version = "v1.0"
        settings.save()

        Consent.record_consent(
            booking=self.booking,
            consent_type=Consent.ConsentType.TERMS_V1,
            policy_version="v1.0",
            source="web_checkin",
        )
        Consent.record_consent(
            booking=self.booking,
            consent_type=Consent.ConsentType.PRIVACY_V1,
            policy_version="v1.0",
            source="web_checkin",
        )

        settings.terms_policy_version = "v2.0"
        settings.privacy_policy_version = "v2.0"
        settings.save()

        checkin_process = CheckInProcess.objects.create(booking=self.booking)

        with self.assertRaises(DataValidationError):
            checkin_process._validate_ready_for_completion()

    @patch('bookings.views.dispatch_email_task')
    def test_newsletter_email_sent_only_after_consent_saved(self, mock_dispatch_email_task):
        token = self.booking.issue_access_token()
        url = reverse('bookings:checkin_wizard', kwargs={'token': token})

        first = Consent.record_consent(
            booking=self.booking,
            consent_type=Consent.ConsentType.TERMS_V1,
            policy_version="v1.0",
            source="web_checkin",
        )
        second = Consent.record_consent(
            booking=self.booking,
            consent_type=Consent.ConsentType.PRIVACY_V1,
            policy_version="v1.0",
            source="web_checkin",
        )

        post_data = {
            'form-TOTAL_FORMS': '1',
            'form-INITIAL_FORMS': '0',
            'form-MIN_NUM_FORMS': '0',
            'form-MAX_NUM_FORMS': '1000',
            'form-0-first_name': 'John',
            'form-0-last_name': 'Doe',
            'form-0-date_of_birth': '1990-01-01',
            'form-0-DELETE': '',
            'terms_and_conditions': 'on',
            'privacy_policy': 'on',
            'newsletter_subscription': 'on',
            'form-0-document_image': create_test_image(),
        }

        with patch.object(Consent, 'record_consent', side_effect=[
            first,
            second,
            DataValidationError(["missing_version"]),
        ]):
            response = self.client.post(
                url,
                data=post_data,
                follow=True,
            )

        self.assertEqual(response.status_code, 200)
        mock_dispatch_email_task.assert_not_called()

    def test_token_expiration(self):
        """Verifica che un token scada correttamente."""
        raw_token = self.booking.issue_access_token()
        # "Sposta" la data di scadenza nel passato
        self.booking.access_token_expires_at = timezone.now() - datetime.timedelta(days=1)
        self.booking.save()
        self.assertFalse(self.booking.verify_access_token(raw_token))

    def test_lock_access(self):
        """Verifica che l'accesso possa essere bloccato."""
        raw_token = self.booking.issue_access_token()
        self.booking.locked_at = timezone.now()
        self.booking.save()
        self.assertFalse(self.booking.verify_access_token(raw_token))

    def test_token_revocation(self):
        """Un token revocato non può più essere validato."""
        raw_token = self.booking.issue_access_token()
        self.booking.revoke_access_token()
        self.assertFalse(self.booking.verify_access_token(raw_token))

    def test_validate_access_token_respects_status(self):
        """La validazione deve filtrare anche per stato quando richiesto."""
        raw_token = self.booking.issue_access_token()
        self.booking.status = Booking.Status.COMPLETED
        self.booking.save(update_fields=["status"])

        booking, reason, _ = Booking.validate_access_token(raw_token, status=Booking.Status.PENDING)
        self.assertEqual(booking, self.booking)
        self.assertEqual(reason, "wrong_status")

    def test_validate_access_token_accepts_signed_token_links(self):
        """I link che contengono il token firmato devono continuare a funzionare."""
        raw_token = self.booking.issue_access_token()

        # Usa direttamente la signature salvata per simulare link legacy
        signed_token = self.booking.access_token_signature

        booking, reason, _ = Booking.validate_access_token(signed_token)

        self.assertEqual(booking, self.booking)
        self.assertIsNone(reason)

    def test_validate_access_token_matches_signature_after_secret_rotation(self):
        """Link con signature salvata devono funzionare anche se il SECRET_KEY cambia."""
        self.booking.issue_access_token()
        signed_token = self.booking.access_token_signature

        with override_settings(SECRET_KEY="new-secret-key"):
            booking, reason, _ = Booking.validate_access_token(signed_token)

        self.assertEqual(booking, self.booking)
        self.assertIsNone(reason)

    def test_validate_access_token_matches_prefix_after_secret_rotation(self):
        """I link raw devono risolversi anche se l'hash usa un SECRET_KEY precedente."""
        raw_token = self.booking.issue_access_token()

        old_secret = "old-secret-key"
        old_signature = signing.dumps(raw_token, salt="booking-access-token", key=old_secret)
        old_hash = salted_hmac("booking-access-token", raw_token, secret=old_secret).hexdigest()

        Booking.objects.filter(id=self.booking.id).update(
            access_token_signature=old_signature,
            access_token_hash=old_hash,
        )

        with override_settings(SECRET_KEY="new-secret-key"):
            booking, reason, _ = Booking.validate_access_token(raw_token)

        self.assertEqual(booking, self.booking)
        self.assertIsNone(reason)


class CheckInWizardRedirectTests(TestCase):

    def setUp(self):
        self.resort = Resort.objects.create(name="Redirect Resort")
        self.booking = Booking.objects.create(
            guest_name="Redirect User",
            guest_email="redirect@example.com",
            check_in_date=timezone.now().date(),
            check_out_date=timezone.now().date() + datetime.timedelta(days=3),
            resort=self.resort,
        )
        self.checkin_process = CheckInProcess.objects.create(booking=self.booking)

    def test_checkin_wizard_redirects_completed_booking(self):
        raw_token = self.booking.issue_access_token()
        self.booking.status = Booking.Status.COMPLETED
        self.booking.save(update_fields=["status"])

        response = self.client.get(reverse('bookings:checkin_wizard', kwargs={'token': raw_token}))

        self.assertRedirects(
            response,
            reverse('bookings:checkin_complete', kwargs={'booking_id': self.booking.id}),
            fetch_redirect_response=False,
        )


class CheckInProcessModelTests(TestCase):

    def setUp(self):
        resort = Resort.objects.create(name="Test Resort OTP")
        booking = Booking.objects.create(
            guest_name="OTP User",
            guest_email="otp@example.com",
            check_in_date=timezone.now().date(),
            check_out_date=timezone.now().date() + datetime.timedelta(days=2),
            resort=resort
        )
        self.checkin_process = CheckInProcess.objects.create(booking=booking)

    def test_issue_and_verify_otp(self):
        """Verifica che un OTP possa essere generato e validato."""
        raw_otp = self.checkin_process.issue_otp()
        self.assertEqual(len(raw_otp), 6)
        result = self.checkin_process.verify_otp(raw_otp)
        self.assertTrue(result['success'])
        # Verifica che l'OTP sia stato invalidato dopo l'uso
        self.assertIsNone(self.checkin_process.otp_code_hash)

    def test_verify_invalid_otp(self):
        """Verifica che un OTP non corretto non venga validato."""
        raw_otp = self.checkin_process.issue_otp()
        result = self.checkin_process.verify_otp("000000")
        self.assertFalse(result['success'])
        # Verifica che il contatore dei tentativi sia aumentato
        self.assertEqual(self.checkin_process.otp_attempts, 1)

    def test_otp_max_attempts(self):
        """Verifica che l'OTP si blocchi dopo troppi tentativi."""
        self.checkin_process.issue_otp()
        for _ in range(5):
            self.checkin_process.verify_otp("111111")
        self.assertEqual(self.checkin_process.otp_attempts, 5)
        locked_result = self.checkin_process.verify_otp("111111")
        self.assertFalse(locked_result['success'])
        self.assertIsNotNone(locked_result.get('locked_until'))


@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
class ImportBookingsCommandTests(TestCase):

    @patch('communications.email_gateway.dispatch_email_task')
    def test_import_command(self, mock_dispatch_email_task):
        """Testa il comando di importazione delle prenotazioni."""
        # Usa get_or_create per essere idempotente rispetto alla migrazione di seeding
        Resort.objects.get_or_create(name="Resort Paradiso")

        # Prepara un file JSON fittizio in memoria
        json_content = """
        [
          {
            "booking_engine_id": "CMD-TEST-01",
            "guest_name": "Command Test",
            "guest_email": "cmd@test.com",
            "check_in_date": "2025-12-01",
            "check_out_date": "2025-12-05",
            "resort_name": "Resort Paradiso"
          }
        ]
        """
        # Crea un file temporaneo fittizio
        with open('dati_test/test_import.json', 'w') as f:
            f.write(json_content)

        # Esegui il comando
        call_command('import_bookings', 'dati_test/test_import.json')

        # Verifica che la prenotazione sia stata creata
        self.assertTrue(Booking.objects.filter(booking_engine_id="CMD-TEST-01").exists())
        # Verifica che il task per inviare l'email sia stato chiamato
        self.assertTrue(mock_dispatch_email_task.called)


@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
class CheckInFlowTests(TestCase):

    def setUp(self):
        """Crea un resort e una prenotazione di base per i test di flusso."""
        self.resort = Resort.objects.create(name="Test Flow Resort")
        self.booking = Booking.objects.create(
            guest_name="Flow Test User",
            guest_email="flow@example.com",
            check_in_date=timezone.now().date(),
            check_out_date=timezone.now().date() + datetime.timedelta(days=3),
            resort=self.resort
        )
        settings = PlatformSettings.load()
        settings.terms_policy_version = "v1.0"
        settings.privacy_policy_version = "v1.0"
        settings.marketing_policy_version = "v1.0"
        settings.save()
        self.checkin_process = CheckInProcess.objects.create(booking=self.booking)
        self.guest = Guest.objects.create(
            booking=self.booking,
            first_name="John",
            last_name="Doe",
            date_of_birth="1990-01-01"
        )
        Consent.objects.create(booking=self.booking, type=Consent.ConsentType.TERMS_V1, policy_version='v1.0', source='web_checkin')
        Consent.objects.create(booking=self.booking, type=Consent.ConsentType.PRIVACY_V1, policy_version='v1.0', source='web_checkin')
        # Crea un file fittizio in memoria
        self.mock_file = create_test_image()
        self.document = GuestDocument.objects.create(
            guest=self.guest,
            file=self.mock_file
        )

    def test_successful_checkin_flow(self):
        """
        Verifica il flusso completo di check-in con un esito positivo.
        I documenti sono scansionati e approvati, permettendo il completamento.
        """
        # Simula il risultato positivo della scansione asincrona
        self.document.scan_result = "clean"
        self.document.ocr_confidence = 0.9
        self.document.scanned_at = timezone.now()
        self.document.save()

        # L'utente ha fornito i dati, si richiede l'OTP
        self.checkin_process.request_otp()
        self.assertEqual(self.checkin_process.state, CheckInProcess.State.AWAITING_OTP)

        # L'utente fornisce l'OTP e firma
        self.checkin_process.sign()
        self.assertEqual(self.checkin_process.state, CheckInProcess.State.SIGNED)

        # Simula la generazione del PDF che avverrebbe nella vista
        now = timezone.now()
        signature_meta = {'ts': now}
        pdf_content, pdf_hash = generate_checkin_pdf(self.booking, signature_meta)
        saved_path = default_storage.save(
            f"signed_documents/checkin_summary_{self.booking.id}_{pdf_hash[:10]}.pdf",
            ContentFile(pdf_content)
        )
        self.checkin_process.signed_pdf_path = saved_path
        self.checkin_process.signed_pdf_url = default_storage.url(saved_path)
        self.checkin_process.signed_pdf_checksum = pdf_hash
        self.checkin_process.pdf_status = CheckInProcess.ArtifactStatus.READY
        self.checkin_process.save()

        # I documenti sono OK, la transizione a 'completed' dovrebbe riuscire
        self.checkin_process.complete()
        self.assertEqual(self.checkin_process.state, CheckInProcess.State.COMPLETED)

        # Verifica che l'URL del PDF sia stato salvato
        self.assertIsNotNone(self.checkin_process.signed_pdf_url)

        # Verifica anche lo stato della prenotazione associata
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, Booking.Status.COMPLETED)

        # Verifica che le transizioni siano state tracciate
        events = list(self.checkin_process.transition_events.all())
        self.assertEqual(len(events), 3)
        self.assertEqual(events[0].to_state, CheckInProcess.State.COMPLETED)

    def test_checkin_flow_needs_review(self):
        """
        Verifica il flusso in cui i documenti non superano la validazione automatica
        e il processo viene messo in stato di revisione.
        """
        # Simula un risultato di scansione che richiede revisione (bassa confidenza)
        self.document.scan_result = "clean"
        self.document.ocr_confidence = 0.4  # Sotto la soglia di 0.6
        self.document.scanned_at = timezone.now()
        self.document.save()

        self.checkin_process.request_otp()
        self.checkin_process.sign()
        self.assertEqual(self.checkin_process.state, CheckInProcess.State.SIGNED)

        # La transizione a 'completed' dovrebbe fallire a causa della condizione
        with self.assertRaises(TransitionNotAllowed):
            self.checkin_process.complete()

        # Il processo dovrebbe essere messo manualmente in revisione
        self.checkin_process.flag_for_review()
        self.assertEqual(self.checkin_process.state, CheckInProcess.State.NEEDS_REVIEW)

        # Lo stato della prenotazione non deve cambiare
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, Booking.Status.PENDING)

    def test_complete_requires_signed_pdf(self):
        self.document.scan_result = "clean"
        self.document.ocr_confidence = 0.9
        self.document.scanned_at = timezone.now()
        self.document.save()

        self.checkin_process.request_otp()
        self.checkin_process.sign()

        with self.assertRaises(DataValidationError):
            self.checkin_process.complete()


@override_settings(CELERY_TASK_ALWAYS_EAGER=True, EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class CheckInWizardRedirectTests(TestCase):
    def setUp(self):
        self.resort = Resort.objects.create(name="Redirect Resort")
        self.booking = Booking.objects.create(
            guest_name="Redirect User",
            guest_email="redirect@example.com",
            check_in_date=timezone.now().date(),
            check_out_date=timezone.now().date() + datetime.timedelta(days=1),
            resort=self.resort,
        )
        self.checkin_process = CheckInProcess.objects.create(
            booking=self.booking,
            state=CheckInProcess.State.AWAITING_OTP,
        )

    @patch('bookings.views.validate_booking_token')
    @patch('bookings.views.CheckInProcess.verify_otp', return_value={'success': True})
    @patch('bookings.views.CheckInProcess.sign', side_effect=TransitionNotAllowed)
    @patch('bookings.views.generate_checkin_pdf_task.apply_async')
    @patch('bookings.views.generate_checkin_qr_task.apply_async')
    def test_redirects_to_dashboard_when_sign_blocked(self, mock_qr_task, mock_pdf_task, mock_sign, mock_verify_otp, mock_validate_token):
        mock_validate_token.return_value = (self.booking, None, 'hash')

        response = self.client.post(
            reverse('bookings:checkin_wizard', args=['token']),
            {'otp_code': '123456'}
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('bookings:dashboard'))


@override_settings(CELERY_TASK_ALWAYS_EAGER=True, EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class EmailTaskEndToEndTests(TestCase):
    def setUp(self):
        self.resort = Resort.objects.create(name="Email Resort")
        self.booking = Booking.objects.create(
            guest_name="Email User",
            guest_email="email@example.com",
            check_in_date=timezone.now().date(),
            check_out_date=timezone.now().date() + datetime.timedelta(days=2),
            resort=self.resort,
        )
        self.checkin_process = CheckInProcess.objects.create(booking=self.booking)

    def test_otp_generation_and_logging(self):
        raw_otp = self.checkin_process.issue_otp()
        result = send_otp_email_task.delay(self.booking.id, raw_otp, 'https', 'testserver')
        self.assertTrue(result.successful())
        self.assertEqual(len(mail.outbox), 1)
        log_entry = EmailLog.objects.filter(task_name='send_otp_email_task', booking=self.booking).first()
        self.assertIsNotNone(log_entry)
        self.assertEqual(log_entry.status, EmailLog.Status.SUCCESS)

    def test_token_reuse_and_link_logging(self):
        link_first = send_booking_creation_email_task.apply(args=[self.booking.id, 'https', 'testserver']).get()
        link_second = send_booking_creation_email_task.apply(args=[self.booking.id, 'https', 'testserver']).get()
        self.assertEqual(link_first, link_second)
        logs = EmailLog.objects.filter(task_name='send_booking_creation_email_task', booking=self.booking)
        self.assertEqual(logs.count(), 2)
        self.assertTrue(all(log.link_used == link_first for log in logs))

    @override_settings(CELERY_TASK_ALWAYS_EAGER=False)
    @patch('bookings.tasks.send_booking_creation_email_task.apply_async', side_effect=Exception("broker down"))
    def test_dispatch_email_task_fallback_to_sync(self, mock_apply_async):
        dispatch_email_task(send_booking_creation_email_task, self.booking.id, 'https', 'testserver')
        self.assertTrue(mock_apply_async.called)
        log_entry = EmailLog.objects.filter(task_name='send_booking_creation_email_task', booking=self.booking).first()
        self.assertIsNotNone(log_entry)
        self.assertEqual(log_entry.status, EmailLog.Status.SUCCESS)

@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
class OcrTaskTests(TestCase):

    def setUp(self):
        """Crea i dati necessari per testare il task OCR."""
        self.resort = Resort.objects.create(name="Test OCR Resort")
        self.booking = Booking.objects.create(
            guest_name="OCR Test User",
            guest_email="ocr@example.com",
            check_in_date=timezone.now().date(),
            check_out_date=timezone.now().date() + datetime.timedelta(days=5),
            resort=self.resort
        )
        self.guest = Guest.objects.create(
            booking=self.booking,
            first_name="Ocr",
            last_name="Test",
            date_of_birth="1990-01-01"
        )

        # Crea un file immagine fittizio
        self.mock_file = create_test_image()
        self.document = GuestDocument.objects.create(
            guest=self.guest,
            file=self.mock_file
        )

    @patch('bookings.tasks.pytesseract.image_to_data')
    @patch('bookings.tasks.Image.open')
    def test_scan_and_ocr_document_task(self, mock_image_open, mock_image_to_data):
        """
        Verifica che il task OCR processi un'immagine, calcoli la confidenza
        e aggiorni correttamente il modello GuestDocument.
        """
        # Configura il mock per ritornare un DataFrame simile a quello di Tesseract
        import pandas as pd
        mock_ocr_data = pd.DataFrame({
            'conf': [95, 80, 70],
            'text': ['NOME', 'COGNOME', 'DATA']
        })
        mock_image_to_data.return_value = mock_ocr_data

        # Esegui il task
        scan_and_ocr_document(self.document.id)

        # Ricarica il documento dal database per verificare le modifiche
        self.document.refresh_from_db()

        # Verifica che i campi siano stati aggiornati correttamente
        self.assertIsNotNone(self.document.scanned_at)
        self.assertEqual(self.document.scan_result, 'clean')

        # Calcola la confidenza attesa (media ponderata)
        # (95*4 + 80*7 + 70*4) / (4+7+4) = (380 + 560 + 280) / 15 = 1220 / 15 = 81.33
        # Normalizzato: 0.8133
        self.assertAlmostEqual(self.document.ocr_confidence, 0.8133, places=4)


class OcrEndpointTests(TestCase):

    def setUp(self):
        self.resort = Resort.objects.create(name="OCR Resort")
        self.booking = Booking.objects.create(
            guest_name="OCR User",
            guest_email="ocr@example.com",
            check_in_date=timezone.now().date(),
            check_out_date=timezone.now().date() + datetime.timedelta(days=1),
            resort=self.resort,
        )
        self.raw_token = self.booking.issue_access_token()

    @patch('bookings.views.perform_ocr')
    def test_ocr_endpoint_returns_fields(self, mock_ocr):
        mock_ocr.return_value = {
            'fields': {
                'first_name': 'Mario',
                'last_name': 'Rossi',
                'document_number': 'AA1234567',
                'document_expiry_date': '2029-12-31',
            },
            'confidence': 0.87,
        }

        image_file = create_test_image()
        base64_img = base64.b64encode(image_file.read()).decode('utf-8')
        payload = {
            'token': self.raw_token,
            'image_base64': f'data:image/png;base64,{base64_img}',
        }

        response = self.client.post(
            '/bookings/api/checkin/ocr/',
            data=json.dumps(payload),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body['fields']['first_name'], 'Mario')
        self.assertEqual(body['fields']['document_number'], 'AA1234567')
        self.assertEqual(body['source'], 'backend')

    def test_ocr_endpoint_requires_token(self):
        response = self.client.post('/bookings/api/checkin/ocr/', {})
        self.assertEqual(response.status_code, 400)


class ClientLogEndpointTests(TestCase):

    def setUp(self):
        self.resort = Resort.objects.create(name="Log Resort")
        self.booking = Booking.objects.create(
            guest_name="Log User",
            guest_email="log@example.com",
            check_in_date=timezone.now().date(),
            check_out_date=timezone.now().date() + datetime.timedelta(days=1),
            resort=self.resort,
        )
        self.raw_token = self.booking.issue_access_token()

    def test_client_log_requires_token(self):
        response = self.client.post('/bookings/api/checkin/logs/', {})
        self.assertEqual(response.status_code, 400)

    def test_client_log_accepts_payload(self):
        payload = {
            'token': self.raw_token,
            'level': 'warn',
            'message': 'Test client issue',
            'context': {'device': 'Pixel 6', 'errorCode': 'NotAllowedError'},
        }

        response = self.client.post(
            '/bookings/api/checkin/logs/',
            data=json.dumps(payload),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'status': 'ok'})
