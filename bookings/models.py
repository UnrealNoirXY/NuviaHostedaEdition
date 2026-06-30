import datetime
import logging
import secrets
from django.db import models, transaction
from django.conf import settings
from django.utils import timezone
from django.core import signing
from django.core.files.storage import default_storage
from django.utils.crypto import salted_hmac
from django.contrib.auth.hashers import make_password, check_password
from django_fsm import FSMField, transition


logger = logging.getLogger(__name__)


class DataValidationError(Exception):
    """Errore sollevato quando i dati per la transizione non sono coerenti."""

    def __init__(self, errors):
        if isinstance(errors, (list, tuple)):
            self.errors = [str(e) for e in errors]
        else:
            self.errors = [str(errors)]
        super().__init__("; ".join(self.errors))

# Modello per tracciare le iscrizioni alla newsletter
class NewsletterSubscription(models.Model):
    email = models.EmailField(unique=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.email

# Modello centrale per la Prenotazione
class Booking(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'In attesa di check-in'
        COMPLETED = 'completed', 'Check-in Completato'
        VERIFIED = 'verified', 'Verificato dallo Staff'
        ARCHIVED = 'archived', 'Archiviato'

    # --- Dati della prenotazione ---
    booking_engine_id = models.CharField(max_length=255, unique=True, null=True, blank=True, help_text="ID univoco dal booking engine esterno")
    guest_name = models.CharField(max_length=255, help_text="Nome del cliente principale")
    guest_email = models.EmailField(help_text="Email del cliente principale")
    check_in_date = models.DateField(verbose_name="Data di Check-in")
    check_out_date = models.DateField(verbose_name="Data di Check-out")
    resort = models.ForeignKey('resort.Resort', on_delete=models.PROTECT, related_name='bookings')
    room_details = models.TextField(blank=True, help_text="Dettagli sulla camera o altre note")

    # --- Sicurezza e Accesso ---
    access_token_hash = models.CharField(max_length=128, blank=True, db_index=True, help_text="Hash del token di accesso per il link 'magico'")
    access_token_signature = models.TextField(blank=True, help_text="Token codificato per riuso controllato")
    access_token_expires_at = models.DateTimeField(null=True, blank=True, help_text="Data di scadenza del token")
    access_token_revoked = models.BooleanField(default=False, help_text="Flag di revoca esplicita del token", db_index=True)
    access_token_revoked_at = models.DateTimeField(null=True, blank=True, help_text="Timestamp della revoca del token")
    locked_at = models.DateTimeField(null=True, blank=True, help_text="Timestamp del blocco per tentativi di brute force")

    # --- Stato e Metadati ---
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    pms_payload_snapshot = models.JSONField(null=True, blank=True, help_text="Snapshot dei dati originali dal booking engine")
    tenant_id = models.CharField(max_length=100, null=True, blank=True, db_index=True, help_text="Per futura gestione multi-proprietà")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Prenotazione per {self.guest_name} dal {self.check_in_date.strftime('%d/%m/%Y')}"

    @staticmethod
    def hash_access_token(raw_token: str) -> str:
        return salted_hmac("booking-access-token", raw_token, secret=settings.SECRET_KEY).hexdigest()

    def issue_access_token(self):
        """Genera un nuovo token di accesso, ne salva l'hash e la scadenza."""
        raw_token = secrets.token_urlsafe(32)  # ~256 bits di entropia
        self.access_token_hash = self.hash_access_token(raw_token)
        self.access_token_signature = signing.dumps(raw_token, salt="booking-access-token")
        self.access_token_expires_at = timezone.now() + datetime.timedelta(days=10)
        self.access_token_revoked = False
        self.access_token_revoked_at = None
        self.locked_at = None # Sblocca in caso di nuovo token
        self.save(update_fields=[
            'access_token_hash',
            'access_token_signature',
            'access_token_expires_at',
            'access_token_revoked',
            'access_token_revoked_at',
            'locked_at'
        ])
        return raw_token

    def revoke_access_token(self, timestamp=None):
        self.access_token_revoked = True
        self.access_token_revoked_at = timestamp or timezone.now()
        self.access_token_signature = ''
        self.save(update_fields=['access_token_revoked', 'access_token_revoked_at', 'access_token_signature'])

    def _get_stored_access_token(self):
        """Ritorna il token esistente se ancora valido."""
        if not self.access_token_signature:
            return None
        try:
            raw_token = signing.loads(self.access_token_signature, salt="booking-access-token")
        except signing.BadSignature:
            return None

        if self.verify_access_token(raw_token):
            return raw_token
        return None

    def ensure_access_token(self):
        """Ritorna un token riutilizzabile o ruota invalidando quello precedente."""
        existing = self._get_stored_access_token()
        if existing:
            return existing

        if self.access_token_hash and not self.access_token_revoked:
            self.revoke_access_token()

        return self.issue_access_token()

    @classmethod
    def validate_access_token(cls, raw_token, status=None):
        token_hash = cls.hash_access_token(raw_token)
        booking = cls.objects.filter(access_token_hash=token_hash).first()

        # Backward compatibility: alcuni link potrebbero contenere il token firmato
        # invece del raw token. In tal caso proviamo a trovare direttamente la
        # signature salvata o a decodificarla e a cercare nuovamente la
        # prenotazione.
        if not booking:
            signature_match = cls.objects.filter(access_token_signature=raw_token).first()
            if signature_match:
                booking = signature_match
                token_hash = booking.access_token_hash
            else:
                try:
                    decoded_token = signing.loads(raw_token, salt="booking-access-token")
                except signing.BadSignature:
                    decoded_token = None

                if decoded_token:
                    token_hash = cls.hash_access_token(decoded_token)
                    booking = cls.objects.filter(access_token_hash=token_hash).first()

            # Extreme backward compatibility: match against the immutable payload
            # prefix of the signed token, ignoring the signature that depends on
            # SECRET_KEY. This lets us find bookings created with an older
            # SECRET_KEY as long as the raw token matches.
            if not booking:
                serializer = signing.JSONSerializer()
                serialized = serializer.dumps(raw_token)
                serialized_bytes = serialized if isinstance(serialized, bytes) else serialized.encode()
                signature_prefix = signing.b64_encode(serialized_bytes).decode()
                booking = cls.objects.filter(
                    access_token_signature__startswith=f"{signature_prefix}:"
                ).first()
                if booking:
                    token_hash = booking.access_token_hash or token_hash

        if not booking:
            return None, 'not_found', token_hash

        if booking.access_token_revoked:
            return None, 'revoked', token_hash

        if booking.access_token_expires_at and timezone.now() > booking.access_token_expires_at:
            return None, 'expired', token_hash

        if booking.locked_at:
            return None, 'locked', token_hash

        if status and booking.status != status:
            return booking, 'wrong_status', token_hash

        return booking, None, token_hash

    def verify_access_token(self, raw_token):
        """Verifica se un token è valido e non scaduto."""
        booking, reason, _ = self.__class__.validate_access_token(raw_token)
        return booking == self and reason is None

    class Meta:
        ordering = ['-check_in_date']
        permissions = [
            ("can_export_bookings", "Can export booking data"),
        ]

def all_docs_ok(process):
    """
    Condizione per la transizione di stato: verifica che tutti i documenti associati
    alla prenotazione siano stati scansionati, siano 'puliti' e abbiano una
    confidenza OCR sufficiente.
    L'istanza passata dalla FSM è il modello `CheckInProcess`.
    """
    booking = process.booking
    # Recupera tutti i documenti associati alla prenotazione tramite i suoi ospiti.
    docs = GuestDocument.objects.filter(guest__booking=booking)

    if not docs.exists():
        return False

    return all(
        d.scan_result == "clean" and d.ocr_confidence is not None and d.ocr_confidence >= 0.6
        for d in docs
    )

# Modello per tracciare il processo di check-in
class CheckInProcess(models.Model):
    OTP_EXPIRY_MINUTES = 10
    OTP_MAX_ATTEMPTS = 5
    OTP_LOCKOUT_MINUTES = 15
    OTP_RESEND_COOLDOWN_SECONDS = 60
    OTP_RATE_LIMIT_ATTEMPTS_PER_MINUTE = 8

    class ArtifactStatus(models.TextChoices):
        PENDING = 'pending', 'In coda'
        PROCESSING = 'processing', 'In elaborazione'
        READY = 'ready', 'Pronto'
        FAILED = 'failed', 'Errore'

    class State(models.TextChoices):
        AWAITING_DATA = 'awaiting_data', 'In attesa di dati'
        AWAITING_OTP = 'awaiting_otp', 'In attesa di OTP'
        SIGNED = 'signed', 'Firmato' # Stato intermedio dopo la firma
        NEEDS_REVIEW = 'needs_review', 'Da Revisionare' # Nuovo stato per revisione manuale
        COMPLETED = 'completed', 'Completato'

    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name='checkin_process')
    state = FSMField(default=State.AWAITING_DATA, choices=State.choices, protected=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # --- Campi per OTP (Step-Up Authentication) ---
    otp_code_hash = models.CharField(max_length=128, blank=True, null=True)
    otp_expires_at = models.DateTimeField(null=True, blank=True)
    otp_attempts = models.PositiveSmallIntegerField(default=0)
    otp_locked_until = models.DateTimeField(null=True, blank=True)
    otp_last_sent_at = models.DateTimeField(null=True, blank=True)

    # --- Campi per Firma Elettronica ---
    signed_pdf_url = models.URLField(blank=True, null=True, help_text="URL al PDF di riepilogo firmato")
    signature_meta = models.JSONField(null=True, blank=True, help_text="Metadati della firma (IP, UA, hash del doc)")
    signed_pdf_path = models.CharField(max_length=512, null=True, blank=True, help_text="Percorso interno del PDF firmato")
    signed_pdf_checksum = models.CharField(max_length=64, null=True, blank=True, help_text="Hash SHA256 del PDF firmato")
    qr_code_path = models.CharField(max_length=512, null=True, blank=True, help_text="Percorso interno del QR code")
    qr_code_url = models.URLField(blank=True, null=True, help_text="URL firmato del QR code")
    pdf_status = models.CharField(max_length=20, choices=ArtifactStatus.choices, default=ArtifactStatus.PENDING)
    qr_status = models.CharField(max_length=20, choices=ArtifactStatus.choices, default=ArtifactStatus.PENDING)

    def __str__(self):
        return f"Processo di Check-in per {self.booking} ({self.get_state_display()})"

    @property
    def otp_attempts_remaining(self):
        return max(0, self.OTP_MAX_ATTEMPTS - self.otp_attempts)

    @property
    def otp_is_locked(self):
        return self.otp_locked_until and timezone.now() < self.otp_locked_until

    def _record_transition_event(self, from_state, to_state, origin=None, user=None, ip_address=None, metadata=None):
        CheckInTransitionEvent.objects.create(
            checkin_process=self,
            booking=self.booking,
            from_state=from_state,
            to_state=to_state,
            origin=origin or CheckInTransitionEvent.Origin.WEB,
            ip_address=ip_address,
            performed_by=user if user and getattr(user, 'is_authenticated', False) else None,
            metadata=metadata or {},
        )

    def _validate_ready_for_completion(self):
        errors = []

        if self.pdf_status != self.ArtifactStatus.READY:
            errors.append("Documento firmato non ancora pronto. Attendiamo la generazione del PDF.")

        if not self.signed_pdf_path or not default_storage.exists(self.signed_pdf_path):
            logger.error(
                "PDF mancante per il booking %s nonostante lo stato di firma.",
                self.booking_id,
                extra={"booking_id": self.booking_id, "signed_pdf_path": self.signed_pdf_path},
            )
            try:
                self.flag_for_review(metadata={"reason": "missing_pdf_artifact"})
            except Exception:
                self.state = self.State.NEEDS_REVIEW
            errors.append("Documento firmato non disponibile. Abbiamo inviato la pratica in revisione.")

        required_consents = {
            Consent.ConsentType.TERMS_V1,
            Consent.ConsentType.PRIVACY_V1,
        }
        current_versions = Consent.get_current_policy_versions()
        for consent_type in required_consents:
            current = (
                self.booking.consents.filter(type=consent_type, status=Consent.Status.CURRENT)
                .order_by('-accepted_at')
                .first()
            )
            if not current:
                errors.append("Consensi obbligatori non salvati. Conferma privacy e termini per completare il check-in.")
                break
            expected_version = current_versions.get(consent_type)
            if expected_version and current.policy_version != expected_version:
                errors.append("La versione della policy non è aggiornata. Rieseguire la conferma dei consensi obbligatori.")
                break

        if errors:
            raise DataValidationError(errors)

    @transition(field=state, source='*', target=State.AWAITING_OTP)
    def request_otp(self, origin=None, user=None, ip_address=None, metadata=None):
        """Transizione per richiedere l'OTP."""
        from_state = self.state
        self._record_transition_event(from_state, self.State.AWAITING_OTP, origin, user, ip_address, metadata)
        logger.info(
            "Richiesta OTP per booking %s: nuovo stato %s", self.booking_id, self.State.AWAITING_OTP,
            extra={"booking_id": self.booking_id, "new_state": self.State.AWAITING_OTP, "ip": ip_address, "user_id": getattr(user, 'id', None)},
        )

    @transition(field=state, source=State.AWAITING_OTP, target=State.SIGNED)
    def sign(self, origin=None, user=None, ip_address=None, metadata=None):
        """Transizione dopo la firma (pre-completamento)."""
        from_state = self.state
        self._record_transition_event(from_state, self.State.SIGNED, origin, user, ip_address, metadata)
        logger.info(
            "Firma registrata per booking %s: nuovo stato %s", self.booking_id, self.State.SIGNED,
            extra={"booking_id": self.booking_id, "new_state": self.State.SIGNED, "ip": ip_address, "user_id": getattr(user, 'id', None)},
        )

    @transition(field=state, source=State.SIGNED, target=State.COMPLETED, conditions=[all_docs_ok])
    def complete(self, origin=None, user=None, ip_address=None, metadata=None):
        """
        Transizione finale a 'completato'.
        Questa transizione è permessa solo se la condizione `all_docs_ok` è soddisfatta.
        """
        self._validate_ready_for_completion()
        self.completed_at = timezone.now()
        self.booking.status = Booking.Status.COMPLETED
        self.booking.save(update_fields=['status'])
        self._record_transition_event(self.State.SIGNED, self.State.COMPLETED, origin, user, ip_address, metadata)
        logger.info(
            "Check-in completato per booking %s: nuovo stato %s", self.booking_id, self.State.COMPLETED,
            extra={"booking_id": self.booking_id, "new_state": self.State.COMPLETED, "ip": ip_address, "user_id": getattr(user, 'id', None)},
        )

    @transition(field=state, source='*', target=State.NEEDS_REVIEW)
    def flag_for_review(self, origin=None, user=None, ip_address=None, metadata=None):
        """Mette il processo in stato di revisione manuale."""
        from_state = self.state
        self._record_transition_event(from_state, self.State.NEEDS_REVIEW, origin, user, ip_address, metadata)
        logger.info(
            "Check-in per booking %s inviato in revisione: nuovo stato %s", self.booking_id, self.State.NEEDS_REVIEW,
            extra={"booking_id": self.booking_id, "new_state": self.State.NEEDS_REVIEW, "ip": ip_address, "user_id": getattr(user, 'id', None)},
        )


    def issue_otp(self):
        """Genera un OTP a 6 cifre, ne salva l'hash e la scadenza."""
        raw_otp = str(secrets.randbelow(1_000_000)).zfill(6)
        self.otp_code_hash = make_password(raw_otp)
        self.otp_expires_at = timezone.now() + datetime.timedelta(minutes=self.OTP_EXPIRY_MINUTES)
        self.otp_attempts = 0
        self.otp_locked_until = None
        self.otp_last_sent_at = timezone.now()
        self.save(update_fields=['otp_code_hash', 'otp_expires_at', 'otp_attempts', 'otp_locked_until', 'otp_last_sent_at'])
        # NOTA: L'invio dell'email con l'OTP avverrà nella vista per separare le responsabilità.
        return raw_otp

    def log_otp_attempt(self, *, success, reason, ip_address=None, user_agent=None, message=None, attempts_remaining=None):
        OTPAttemptLog.objects.create(
            checkin_process=self,
            booking=self.booking,
            ip_address=ip_address,
            user_agent=user_agent,
            was_successful=success,
            reason=reason,
            message=message,
            attempts_remaining=attempts_remaining,
        )

    def verify_otp(self, raw_otp, *, ip_address=None, user_agent=None):
        """Verifica un OTP, restituendo un dizionario con esito e messaggio UX."""
        now = timezone.now()

        if self.otp_is_locked:
            message = "Troppi tentativi non validi. Accesso temporaneamente bloccato."
            self.log_otp_attempt(
                success=False,
                reason='locked',
                ip_address=ip_address,
                user_agent=user_agent,
                message=message,
                attempts_remaining=0,
            )
            return {
                'success': False,
                'message': message,
                'locked_until': self.otp_locked_until,
                'attempts_remaining': 0,
            }

        if not self.otp_code_hash or not self.otp_expires_at:
            message = "Nessun OTP attivo. Richiedi un nuovo codice."
            self.log_otp_attempt(
                success=False,
                reason='missing',
                ip_address=ip_address,
                user_agent=user_agent,
                message=message,
                attempts_remaining=self.otp_attempts_remaining,
            )
            return {
                'success': False,
                'message': message,
                'attempts_remaining': self.otp_attempts_remaining,
            }

        if now > self.otp_expires_at:
            message = "Il codice è scaduto. Richiedi un nuovo OTP."
            self.log_otp_attempt(
                success=False,
                reason='expired',
                ip_address=ip_address,
                user_agent=user_agent,
                message=message,
                attempts_remaining=self.otp_attempts_remaining,
            )
            return {
                'success': False,
                'message': message,
                'attempts_remaining': self.otp_attempts_remaining,
            }

        is_correct = check_password(str(raw_otp), self.otp_code_hash)
        if not is_correct:
            self.otp_attempts += 1
            attempts_remaining = self.otp_attempts_remaining
            update_fields = ['otp_attempts']
            message = f"Codice errato. Hai ancora {attempts_remaining} tentativi."

            if self.otp_attempts >= self.OTP_MAX_ATTEMPTS:
                self.otp_locked_until = now + datetime.timedelta(minutes=self.OTP_LOCKOUT_MINUTES)
                update_fields.append('otp_locked_until')
                message = (
                    "Tentativi esauriti. Accesso bloccato per "
                    f"{self.OTP_LOCKOUT_MINUTES} minuti."
                )
                AuditLog.objects.create(
                    action=AuditLog.Action.LOCKED_ACCESS,
                    target_booking=self.booking,
                    details={"ip": ip_address},
                )

            self.save(update_fields=update_fields)
            self.log_otp_attempt(
                success=False,
                reason='invalid_code',
                ip_address=ip_address,
                user_agent=user_agent,
                message=message,
                attempts_remaining=attempts_remaining,
            )
            return {
                'success': False,
                'message': message,
                'locked_until': self.otp_locked_until,
                'attempts_remaining': attempts_remaining,
            }

        # L'OTP è corretto, lo invalidiamo per prevenire riutilizzo
        self.otp_code_hash = None
        self.otp_expires_at = None
        self.otp_attempts = 0
        self.otp_locked_until = None
        self.save(update_fields=['otp_code_hash', 'otp_expires_at', 'otp_attempts', 'otp_locked_until'])
        self.log_otp_attempt(
            success=True,
            reason='verified',
            ip_address=ip_address,
            user_agent=user_agent,
            message='OTP verificato con successo',
            attempts_remaining=self.OTP_MAX_ATTEMPTS,
        )

        return {
            'success': True,
            'message': 'OTP verificato con successo',
            'attempts_remaining': self.OTP_MAX_ATTEMPTS,
        }


class CheckInTransitionEvent(models.Model):
    class Origin(models.TextChoices):
        WEB = 'web', 'Web'
        MOBILE = 'mobile', 'Mobile'
        ADMIN = 'admin', 'Admin'
        SYSTEM = 'system', 'Sistema'

    checkin_process = models.ForeignKey('CheckInProcess', on_delete=models.CASCADE, related_name='transition_events')
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='checkin_events')
    from_state = models.CharField(max_length=50)
    to_state = models.CharField(max_length=50)
    origin = models.CharField(max_length=20, choices=Origin.choices, default=Origin.WEB)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    performed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    metadata = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Transizione {self.from_state} -> {self.to_state} per booking {self.booking_id}"


# Modello per ogni singolo ospite della prenotazione
class Guest(models.Model):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='guests')
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    date_of_birth = models.DateField()
    document_number = models.CharField(max_length=64, blank=True)
    document_expiry_date = models.DateField(null=True, blank=True)
    # Aggiungere altri campi anagrafici richiesti dalla legge (luogo di nascita, nazionalità, etc.)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


# Modello per il documento d'identità di un ospite
class GuestDocument(models.Model):
    guest = models.OneToOneField(Guest, on_delete=models.CASCADE, related_name='document')
    file = models.FileField(upload_to='guest_documents/%Y/%m/%d/', help_text="File del documento d'identità", null=True, blank=True)
    sha256_hash = models.CharField(max_length=64, blank=True, help_text="Hash del file per verificarne l'integrità")
    scanned_at = models.DateTimeField(null=True, blank=True, help_text="Timestamp della scansione antivirus/OCR")
    scan_result = models.CharField(max_length=20, blank=True, null=True, help_text="Risultato della scansione (es. 'clean', 'infected')")
    ocr_confidence = models.FloatField(null=True, blank=True, help_text="Punteggio di confidenza dell'estrazione OCR")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Documento di {self.guest}"

    class Meta:
        permissions = [
            ("can_verify_document", "Can verify guest document"),
        ]


# Modello per tracciare i consensi
class Consent(models.Model):
    class ConsentType(models.TextChoices):
        TERMS_V1 = 'terms_v1', 'Termini e Condizioni v1.0'
        PRIVACY_V1 = 'privacy_v1', 'Informativa Privacy v1.0'
        MARKETING_NEWSLETTER = 'marketing_newsletter', 'Iscrizione Newsletter'

    class Status(models.TextChoices):
        CURRENT = 'current', 'Current'
        SUPERSEDED = 'superseded', 'Superseded'

    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='consents')
    type = models.CharField(max_length=50, choices=ConsentType.choices)
    granted_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(default=timezone.now, help_text="Timestamp di accettazione della policy")
    policy_version = models.CharField(max_length=50, help_text="Es. 'v1.2 del 2024-09-26'")
    source = models.CharField(max_length=50, help_text="Origine del consenso (es. web_checkin, email)")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.CURRENT, db_index=True)
    superseded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['booking', 'type'],
                condition=models.Q(status='current'),
                name='unique_current_consent_per_type',
            )
        ]

    def __str__(self):
        return f"Consenso '{self.get_type_display()}' per {self.booking}"

    @classmethod
    def get_current_policy_versions(cls):
        from core.models import PlatformSettings

        settings = PlatformSettings.load()
        return {
            cls.ConsentType.TERMS_V1: settings.terms_policy_version,
            cls.ConsentType.PRIVACY_V1: settings.privacy_policy_version,
            cls.ConsentType.MARKETING_NEWSLETTER: settings.marketing_policy_version,
        }

    @classmethod
    def record_consent(
        cls,
        *,
        booking,
        consent_type,
        policy_version,
        source,
        ip_address=None,
        user_agent=None,
    ):
        if not policy_version:
            raise DataValidationError(f"Versione di policy mancante per il consenso {consent_type}")

        with transaction.atomic():
            now = timezone.now()
            cls.objects.filter(booking=booking, type=consent_type, status=cls.Status.CURRENT).update(
                status=cls.Status.SUPERSEDED,
                superseded_at=now,
            )
            return cls.objects.create(
                booking=booking,
                type=consent_type,
                policy_version=policy_version,
                source=source,
                ip_address=ip_address,
                user_agent=user_agent,
                accepted_at=now,
            )


# Modello per l'Audit Log delle azioni dello staff
class AuditLog(models.Model):
    class Action(models.TextChoices):
        VIEWED_DOCUMENT = 'viewed_document', 'Visualizzato Documento'
        EXPORTED_DATA = 'exported_data', 'Esportato Dati'
        REGENERATED_TOKEN = 'regenerated_token', 'Rigenerato Token'
        LOCKED_ACCESS = 'locked_access', 'Bloccato Accesso'
        UNLOCKED_ACCESS = 'unlocked_access', 'Sbloccato Accesso'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='audit_logs')
    action = models.CharField(max_length=50, choices=Action.choices)
    target_booking = models.ForeignKey(Booking, on_delete=models.CASCADE, null=True, blank=True, related_name='audit_logs')
    target_guest = models.ForeignKey(Guest, on_delete=models.CASCADE, null=True, blank=True, related_name='audit_logs')
    details = models.JSONField(null=True, blank=True, help_text="Dettagli aggiuntivi, come l'indirizzo IP")
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Azione '{self.get_action_display()}' eseguita da {self.user} il {self.timestamp.strftime('%d/%m/%Y %H:%M')}"

    class Meta:
        ordering = ['-timestamp']


class OTPAttemptLog(models.Model):
    checkin_process = models.ForeignKey(CheckInProcess, on_delete=models.CASCADE, related_name='otp_attempts_log')
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='otp_attempts_log')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    was_successful = models.BooleanField(default=False)
    reason = models.CharField(max_length=50)
    message = models.TextField(null=True, blank=True)
    attempts_remaining = models.PositiveSmallIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Tentativo OTP per {self.booking_id} - {'OK' if self.was_successful else 'KO'}"