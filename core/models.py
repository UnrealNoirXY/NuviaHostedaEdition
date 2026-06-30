from django.db import models
from django.core.exceptions import ValidationError
from django.conf import settings
import secrets


class InAppGuideAssetQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)

class PlatformSettings(models.Model):
    """
    A singleton model to store global platform settings.
    Ensures that only one instance of these settings can be created.
    """
    platform_name = models.CharField(max_length=100, default='Noir Tools Kit')
    primary_color = models.CharField(max_length=7, default='#23395d', help_text="Colore primario in formato esadecimale (es. #RRGGBB)")
    secondary_color = models.CharField(max_length=7, default='#406fa6', help_text="Colore secondario in formato esadecimale (es. #RRGGBB)")
    maintenance_mode = models.BooleanField(
        default=False,
        verbose_name="Attiva Modalità Manutenzione",
        help_text="Se attivata, solo i Superadmin potranno accedere al sito. Tutti gli altri utenti verranno reindirizzati a una pagina di manutenzione."
    )
    terms_policy_version = models.CharField(
        max_length=50,
        default='v1.0',
        help_text="Versione corrente dei Termini e Condizioni",
    )
    privacy_policy_version = models.CharField(
        max_length=50,
        default='v1.0',
        help_text="Versione corrente dell'informativa Privacy",
    )
    marketing_policy_version = models.CharField(
        max_length=50,
        default='v1.0',
        help_text="Versione corrente per il consenso marketing/newsletter",
    )

    class Meta:
        verbose_name = "Impostazioni Piattaforma"
        verbose_name_plural = "Impostazioni Piattaforma"

    def __str__(self):
        return "Impostazioni della Piattaforma"

    def save(self, *args, **kwargs):
        """
        Overrides the save method to ensure only one instance of PlatformSettings exists.
        """
        if not self.pk and PlatformSettings.objects.exists():
            # If trying to create a new instance and one already exists,
            # raise an error.
            raise ValidationError('Può esistere una sola istanza delle Impostazioni Piattaforma.')
        return super(PlatformSettings, self).save(*args, **kwargs)

    @classmethod
    def load(cls):
        """
        Load the singleton instance, creating it if it doesn't exist.
        """
        obj, created = cls.objects.get_or_create(pk=1)
        return obj

class TrustedDevice(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='trusted_devices')
    token = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Trusted device for {self.user.username} created at {self.created_at.strftime('%Y-%m-%d %H:%M')}"

    @staticmethod
    def generate_token():
        return secrets.token_urlsafe(64)


class InAppGuideAsset(models.Model):
    TYPE_VIDEO = 'video'
    TYPE_IMAGE = 'image'
    TYPE_LINK = 'link'

    TYPE_CHOICES = (
        (TYPE_VIDEO, 'Video'),
        (TYPE_IMAGE, 'Immagine'),
        (TYPE_LINK, 'Link'),
    )

    guide_key = models.CharField(max_length=100, db_index=True)
    step_key = models.CharField(max_length=150, db_index=True)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    resource_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    url = models.URLField()
    thumbnail_url = models.URLField(blank=True)
    position = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='created_guide_assets',
    )
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = InAppGuideAssetQuerySet.as_manager()

    class Meta:
        ordering = ('position', 'created_at')
        verbose_name = 'Risorsa guida in-app'
        verbose_name_plural = 'Risorse guida in-app'
        indexes = [
            models.Index(fields=('guide_key', 'step_key')),
        ]

    def __str__(self):
        return f"{self.get_resource_type_display()} · {self.title}"

    def as_payload(self):
        return {
            'id': self.pk,
            'title': self.title,
            'description': self.description,
            'type': self.resource_type,
            'url': self.url,
            'thumbnail': self.thumbnail_url,
            'step_key': self.step_key,
            'managed': True,
        }


class AdminLogEntry(models.Model):
    ACCESS = "access"
    PASSWORD_CHANGE = "password_change"
    PAYSLIP = "payslip"
    COMMUNICATION = "communication"
    INTELLECTUAL_PROPERTY = "intellectual_property"
    DATA = "data"
    OTHER = "other"

    ACTION_CHOICES = (
        (ACCESS, "Accessi"),
        (PASSWORD_CHANGE, "Cambio password"),
        (PAYSLIP, "Buste paga"),
        (COMMUNICATION, "Comunicazioni"),
        (INTELLECTUAL_PROPERTY, "Proprietà intellettuale"),
        (DATA, "Dati"),
        (OTHER, "Altro"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="admin_logs",
    )
    action_type = models.CharField(max_length=50, choices=ACTION_CHOICES, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    description = models.TextField(blank=True)
    extra = models.JSONField(blank=True, default=dict)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ("-timestamp",)
        verbose_name = "Log amministratore"
        verbose_name_plural = "Log amministratore"

    def __str__(self):
        action = self.get_action_type_display()
        user_label = self.user.get_full_name() if self.user else "Sistema"
        return f"{action} - {user_label} ({self.timestamp:%Y-%m-%d %H:%M})"



class NuviaMailAccount(models.Model):
    PROVIDER_GOOGLE = 'google'
    PROVIDER_MICROSOFT = 'microsoft'
    PROVIDER_IMAP = 'imap'
    PROVIDER_CHOICES = (
        (PROVIDER_GOOGLE, 'Google Workspace'),
        (PROVIDER_MICROSOFT, 'Microsoft 365'),
        (PROVIDER_IMAP, 'IMAP/SMTP generico'),
    )

    AUTH_OAUTH = 'oauth'
    AUTH_PASSWORD = 'password'
    AUTH_APP_PASSWORD = 'app_password'
    AUTH_MODE_CHOICES = (
        (AUTH_OAUTH, 'OAuth'),
        (AUTH_PASSWORD, 'Password'),
        (AUTH_APP_PASSWORD, 'App Password'),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='nuvia_mail_accounts')
    email_address = models.EmailField()
    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES, default=PROVIDER_IMAP)
    auth_mode = models.CharField(max_length=20, choices=AUTH_MODE_CHOICES, default=AUTH_APP_PASSWORD)
    imap_host = models.CharField(max_length=255, blank=True)
    imap_port = models.PositiveIntegerField(default=993)
    smtp_host = models.CharField(max_length=255, blank=True)
    smtp_port = models.PositiveIntegerField(default=587)
    use_ssl = models.BooleanField(default=True)
    use_starttls = models.BooleanField(default=True)
    username = models.CharField(max_length=255, blank=True)
    encrypted_password = models.TextField(blank=True)
    encrypted_oauth_access_token = models.TextField(blank=True)
    encrypted_oauth_refresh_token = models.TextField(blank=True)
    oauth_access_token_masked = models.CharField(max_length=255, blank=True)
    oauth_refresh_token_masked = models.CharField(max_length=255, blank=True)
    oauth_token_expires_at = models.DateTimeField(null=True, blank=True)
    oauth_connected_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    last_test_status = models.CharField(max_length=20, blank=True)
    last_test_message = models.CharField(max_length=255, blank=True)
    last_test_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Account Nuvia Mail'
        verbose_name_plural = 'Account Nuvia Mail'
        ordering = ('-updated_at',)
        constraints = [
            models.UniqueConstraint(fields=['user', 'email_address'], name='uniq_nuvia_mail_user_email'),
        ]

    def __str__(self):
        return f"{self.user} · {self.email_address}"

    def set_password(self, raw_password):
        from .nuvia_mail_security import encrypt_value
        self.encrypted_password = encrypt_value(raw_password)

    def get_password(self):
        from .nuvia_mail_security import decrypt_value
        return decrypt_value(self.encrypted_password)

    def set_oauth_tokens(self, access_token, refresh_token):
        from .nuvia_mail_security import encrypt_value
        self.encrypted_oauth_access_token = encrypt_value(access_token)
        self.encrypted_oauth_refresh_token = encrypt_value(refresh_token)

    def get_oauth_tokens(self):
        from .nuvia_mail_security import decrypt_value
        return (
            decrypt_value(self.encrypted_oauth_access_token),
            decrypt_value(self.encrypted_oauth_refresh_token)
        )


class NuviaMailSignature(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='nuvia_mail_signatures')
    account = models.ForeignKey(NuviaMailAccount, on_delete=models.CASCADE, related_name='signatures', null=True, blank=True)
    name = models.CharField(max_length=80, default='Firma standard')
    body = models.TextField()
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Firma Nuvia Mail'
        verbose_name_plural = 'Firme Nuvia Mail'
        ordering = ('-is_default', '-updated_at')

    def __str__(self):
        return f"{self.user} · {self.name}"


class NuviaMailOnboardingEvent(models.Model):
    EVENT_LANDING_VISIT = 'landing_visit'
    EVENT_ACCOUNT_SAVED = 'account_saved'
    EVENT_CONNECTION_TESTED = 'connection_tested'
    EVENT_SIGNATURE_SAVED = 'signature_saved'
    EVENT_QUEUE_ITEM_CREATED = 'queue_item_created'
    EVENT_QUEUE_PROCESSED = 'queue_processed'
    EVENT_QUEUE_ITEM_APPROVED = 'queue_item_approved'
    EVENT_QUEUE_ITEM_REJECTED = 'queue_item_rejected'

    EVENT_CHOICES = (
        (EVENT_LANDING_VISIT, 'Landing visit'),
        (EVENT_ACCOUNT_SAVED, 'Account saved'),
        (EVENT_CONNECTION_TESTED, 'Connection tested'),
        (EVENT_SIGNATURE_SAVED, 'Signature saved'),
        (EVENT_QUEUE_ITEM_CREATED, 'Queue item created'),
        (EVENT_QUEUE_PROCESSED, 'Queue processed'),
        (EVENT_QUEUE_ITEM_APPROVED, 'Queue item approved'),
        (EVENT_QUEUE_ITEM_REJECTED, 'Queue item rejected'),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='nuvia_mail_events')
    event_type = models.CharField(max_length=40, choices=EVENT_CHOICES)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Evento onboarding Nuvia Mail'
        verbose_name_plural = 'Eventi onboarding Nuvia Mail'
        ordering = ('-created_at',)
        indexes = [
            models.Index(fields=['user', 'event_type', 'created_at']),
        ]

    def __str__(self):
        return f"{self.user} · {self.event_type}"


class NuviaMailTemplate(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='nuvia_mail_templates')
    name = models.CharField(max_length=100)
    subject = models.CharField(max_length=180)
    body = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Template Nuvia Mail'
        verbose_name_plural = 'Template Nuvia Mail'
        ordering = ('name',)
        constraints = [
            models.UniqueConstraint(fields=['user', 'name'], name='uniq_nuvia_mail_template_user_name'),
        ]

    def __str__(self):
        return f"{self.user} · {self.name}"


class NuviaMailSendQueue(models.Model):
    STATUS_QUEUED = 'queued'
    STATUS_SENT = 'sent'
    STATUS_FAILED = 'failed'
    STATUS_PENDING_APPROVAL = 'pending_approval'
    STATUS_CHOICES = (
        (STATUS_QUEUED, 'In coda'),
        (STATUS_SENT, 'Inviata'),
        (STATUS_FAILED, 'Errore'),
        (STATUS_PENDING_APPROVAL, 'In attesa approvazione'),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='nuvia_mail_send_queue')
    account = models.ForeignKey(NuviaMailAccount, on_delete=models.SET_NULL, null=True, blank=True, related_name='send_queue_items')
    to_email = models.EmailField()
    cc = models.CharField(max_length=255, blank=True)
    bcc = models.CharField(max_length=255, blank=True)
    subject = models.CharField(max_length=180)
    body = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_QUEUED)
    scheduled_for = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    error_message = models.CharField(max_length=255, blank=True)
    retry_count = models.PositiveIntegerField(default=0)
    max_retries = models.PositiveIntegerField(default=3)
    last_attempt_at = models.DateTimeField(null=True, blank=True)
    provider_message_id = models.CharField(max_length=255, blank=True)
    compliance_flagged = models.BooleanField(default=False)
    compliance_reason = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Coda invio Nuvia Mail'
        verbose_name_plural = 'Coda invio Nuvia Mail'
        ordering = ('-created_at',)

    def __str__(self):
        return f"{self.user} · {self.to_email} · {self.status}"


class NuviaMailCompliancePolicy(models.Model):
    ACTION_MARK_FAILED = 'mark_failed'
    ACTION_REQUIRE_APPROVAL = 'require_approval'
    FLAG_ACTION_CHOICES = (
        (ACTION_MARK_FAILED, 'Blocca invio'),
        (ACTION_REQUIRE_APPROVAL, 'Richiedi approvazione'),
    )

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='nuvia_mail_compliance_policy')
    enforce_external_domain_block = models.BooleanField(default=False)
    allowed_domains = models.TextField(blank=True, help_text='Domini consentiti separati da virgola, es: azienda.it,partner.com')
    blocked_domains = models.TextField(blank=True, help_text='Domini sempre bloccati separati da virgola.')
    blocked_recipients = models.TextField(blank=True, help_text='Indirizzi email sempre bloccati separati da virgola.')
    sensitive_keywords = models.TextField(blank=True, help_text='Parole chiave sensibili separate da virgola.')
    sensitive_regex_patterns = models.TextField(blank=True, help_text='Pattern regex sensibili separati da virgola.')
    flagged_action = models.CharField(max_length=20, choices=FLAG_ACTION_CHOICES, default=ACTION_REQUIRE_APPROVAL)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Policy compliance Nuvia Mail'
        verbose_name_plural = 'Policy compliance Nuvia Mail'

    def __str__(self):
        return f"Policy Nuvia Mail · {self.user}"


class NuviaMailFolder(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='nuvia_mail_folders')
    account = models.ForeignKey(NuviaMailAccount, on_delete=models.CASCADE, related_name='folders')
    provider_folder_id = models.CharField(max_length=255)
    name = models.CharField(max_length=120)
    is_inbox = models.BooleanField(default=False)
    is_sent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Cartella Nuvia Mail'
        verbose_name_plural = 'Cartelle Nuvia Mail'
        ordering = ('name',)
        constraints = [
            models.UniqueConstraint(fields=['account', 'provider_folder_id'], name='uniq_nuvia_mail_folder_provider_id'),
        ]

    def __str__(self):
        return f"{self.user} · {self.name}"


class NuviaMailThread(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='nuvia_mail_threads')
    account = models.ForeignKey(NuviaMailAccount, on_delete=models.CASCADE, related_name='threads')
    folder = models.ForeignKey(NuviaMailFolder, on_delete=models.CASCADE, related_name='threads')
    provider_thread_id = models.CharField(max_length=255, blank=True)
    subject = models.CharField(max_length=255, blank=True)
    last_message_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Thread Nuvia Mail'
        verbose_name_plural = 'Thread Nuvia Mail'
        ordering = ('-last_message_at', '-updated_at')
        indexes = [
            models.Index(fields=['user', 'last_message_at']),
        ]

    def __str__(self):
        return f"{self.user} · {self.subject or 'Thread'}"


class NuviaMailMessage(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='nuvia_mail_messages')
    account = models.ForeignKey(NuviaMailAccount, on_delete=models.CASCADE, related_name='messages')
    folder = models.ForeignKey(NuviaMailFolder, on_delete=models.CASCADE, related_name='messages')
    thread = models.ForeignKey(NuviaMailThread, on_delete=models.CASCADE, related_name='messages')
    provider_message_id = models.CharField(max_length=255)
    message_id_header = models.CharField(max_length=255, blank=True)
    in_reply_to = models.CharField(max_length=255, blank=True)
    references_header = models.TextField(blank=True)
    from_email = models.EmailField(blank=True)
    to_emails = models.TextField(blank=True)
    cc_emails = models.TextField(blank=True)
    bcc_emails = models.TextField(blank=True)
    subject = models.CharField(max_length=255, blank=True)
    body_text = models.TextField(blank=True)
    body_html = models.TextField(blank=True)
    received_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Messaggio Nuvia Mail'
        verbose_name_plural = 'Messaggi Nuvia Mail'
        ordering = ('-received_at', '-created_at')
        constraints = [
            models.UniqueConstraint(fields=['account', 'provider_message_id'], name='uniq_nuvia_mail_message_provider_id'),
        ]

    def __str__(self):
        return f"{self.user} · {self.subject or self.provider_message_id}"


class NuviaMailSyncCheckpoint(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='nuvia_mail_sync_checkpoints')
    account = models.ForeignKey(NuviaMailAccount, on_delete=models.CASCADE, related_name='sync_checkpoints')
    folder = models.ForeignKey(NuviaMailFolder, on_delete=models.CASCADE, related_name='sync_checkpoints')
    cursor = models.CharField(max_length=255, blank=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)
    last_error = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Checkpoint sync Nuvia Mail'
        verbose_name_plural = 'Checkpoint sync Nuvia Mail'
        constraints = [
            models.UniqueConstraint(fields=['account', 'folder'], name='uniq_nuvia_mail_sync_checkpoint_folder'),
        ]

    def __str__(self):
        return f"Checkpoint · {self.user} · {self.folder.name}"
