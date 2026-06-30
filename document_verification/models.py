import uuid
from django.db import models

class VerifiedDocument(models.Model):
    class VerificationStatus(models.TextChoices):
        PENDING = 'PENDING', 'In attesa'
        VERIFIED = 'VERIFIED', 'Verificato'
        NEEDS_REVIEW = 'NEEDS_REVIEW', 'Richiede revisione manuale'
        FAILED = 'FAILED', 'Verifica fallita'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Stato della verifica
    status = models.CharField(
        max_length=20,
        choices=VerificationStatus.choices,
        default=VerificationStatus.PENDING,
    )

    # Campi estratti
    document_number = models.CharField(max_length=255, blank=True, null=True)
    first_name = models.CharField(max_length=255, blank=True, null=True)
    last_name = models.CharField(max_length=255, blank=True, null=True)
    birth_date = models.DateField(blank=True, null=True)
    expiry_date = models.DateField(blank=True, null=True)
    issuer_country = models.CharField(max_length=3, blank=True, null=True) # ISO 3166-1 alpha-3

    # Dati grezzi e confidenza
    raw_ocr_response = models.JSONField(default=dict)
    confidence_scores = models.JSONField(default=dict)

    # Note per la revisione
    review_notes = models.TextField(blank=True)

    def __str__(self):
        return f"Documento {self.id} - Stato: {self.get_status_display()}"

    class Meta:
        verbose_name = "Documento Verificato"
        verbose_name_plural = "Documenti Verificati"
        ordering = ['-created_at']
