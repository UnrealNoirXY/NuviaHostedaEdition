import io
import importlib.util
import re
import uuid
from pathlib import Path
from zipfile import ZipFile

from django.conf import settings
from django.core.exceptions import SuspiciousFileOperation
from django.core.files.base import ContentFile
from django.db import models, transaction
from django.utils import timezone
from django.utils.text import slugify
from pypdf import PdfReader, PdfWriter


class HRDocument(models.Model):
    CATEGORY_CHOICES = [
        ("notice", "Comunicazione"),
        ("policy", "Policy"),
        ("form", "Modulo"),
        ("other", "Altro"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default="notice")
    file = models.FileField(upload_to="hr/documents/")
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="hr_documents_uploaded"
    )
    audience_roles = models.JSONField(blank=True, default=list, help_text="Ruoli destinatari")
    audience_company = models.ForeignKey(
        "clients.Company",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="hr_documents",
    )
    audience_resort = models.ForeignKey(
        "resort.Resort",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="hr_documents",
    )
    requires_acknowledgement = models.BooleanField(default=False)
    acknowledged_by = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name="hr_documents_acknowledged")
    visible_from = models.DateTimeField(default=timezone.now)
    visible_until = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["category", "visible_from"]),
            models.Index(fields=["visible_from", "visible_until"]),
        ]

    def __str__(self):
        return self.title

    def is_visible_for(self, user):
        if self.visible_from and self.visible_from > timezone.now():
            return False
        if self.visible_until and self.visible_until < timezone.now():
            return False

        if self.audience_company_id and getattr(user, "company_id", None) not in (self.audience_company_id, None):
            return False
        if self.audience_resort_id and getattr(user, "resort_id", None) not in (self.audience_resort_id, None):
            return False
        if self.audience_roles and getattr(user, "role", None) not in self.audience_roles:
            return False
        return True


class NotificationPreference(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="hr_notification_preferences")
    allow_email = models.BooleanField(default=True)
    allow_push = models.BooleanField(default=True)
    allow_sms = models.BooleanField(default=False)
    quiet_hours_start = models.TimeField(null=True, blank=True)
    quiet_hours_end = models.TimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Preferenza di notifica"
        verbose_name_plural = "Preferenze di notifica"

    def __str__(self):
        return f"Preferenze notifiche per {getattr(self.user, 'username', '')}"


class HRNotification(models.Model):
    STATUS_DRAFT = "draft"
    STATUS_PUBLISHED = "published"
    STATUS_ARCHIVED = "archived"
    STATUS_CHOICES = [
        (STATUS_DRAFT, "Bozza"),
        (STATUS_PUBLISHED, "Pubblicata"),
        (STATUS_ARCHIVED, "Archiviata"),
    ]

    CATEGORY_CHOICES = [
        ("general", "Generale"),
        ("alert", "Allerta"),
        ("payroll", "Buste paga"),
        ("event", "Evento"),
    ]
    CTA_TYPE_PRIMARY = "primary"
    CTA_TYPE_SECONDARY = "secondary"
    CTA_TYPE_CHOICES = [
        (CTA_TYPE_PRIMARY, "Primaria"),
        (CTA_TYPE_SECONDARY, "Secondaria"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    body = models.TextField()
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES, default="general")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT, db_index=True)
    scheduled_for = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    cta_label = models.CharField(max_length=120, blank=True, default="")
    cta_url = models.CharField(max_length=500, blank=True, default="")
    cta_type = models.CharField(max_length=20, choices=CTA_TYPE_CHOICES, default=CTA_TYPE_PRIMARY)
    audience_roles = models.JSONField(blank=True, default=list, help_text="Ruoli destinatari")
    audience_company = models.ForeignKey(
        "clients.Company",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="hr_notifications",
    )
    audience_resort = models.ForeignKey(
        "resort.Resort",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="hr_notifications",
    )
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="hr_notifications_created")
    delivered_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status", "scheduled_for", "expires_at"])]

    def __str__(self):
        return self.title

    def is_visible_for(self, user):
        now = timezone.now()
        if self.status != self.STATUS_PUBLISHED:
            return False
        if self.scheduled_for and self.scheduled_for > now:
            return False
        if self.expires_at and self.expires_at < now:
            return False
        if self.audience_company_id and getattr(user, "company_id", None) not in (self.audience_company_id, None):
            return False
        if self.audience_resort_id and getattr(user, "resort_id", None) not in (self.audience_resort_id, None):
            return False
        if self.audience_roles and getattr(user, "role", None) not in self.audience_roles:
            return False
        return True


class HRNotificationDelivery(models.Model):
    CHANNEL_EMAIL = "email"
    CHANNEL_PUSH = "push"
    CHANNEL_SMS = "sms"
    CHANNEL_CHOICES = [
        (CHANNEL_EMAIL, "Email"),
        (CHANNEL_PUSH, "Push"),
        (CHANNEL_SMS, "SMS"),
    ]

    STATUS_PENDING = "pending"
    STATUS_DELIVERED = "delivered"
    STATUS_FAILED = "failed"
    STATUS_SKIPPED = "skipped"
    STATUS_CHOICES = [
        (STATUS_PENDING, "In attesa"),
        (STATUS_DELIVERED, "Consegnato"),
        (STATUS_FAILED, "Fallito"),
        (STATUS_SKIPPED, "Ignorato"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    notification = models.ForeignKey(
        HRNotification, on_delete=models.CASCADE, related_name="deliveries"
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    channel = models.CharField(max_length=16, choices=CHANNEL_CHOICES, db_index=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_PENDING)
    sent_at = models.DateTimeField(null=True, blank=True)
    error = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = ("notification", "user", "channel")
        indexes = [models.Index(fields=["status", "sent_at"])]

    def __str__(self):
        return f"Delivery {self.notification_id} to {getattr(self.user, 'username', '')} via {self.channel}"


class PayslipBatch(models.Model):
    STATUS_PENDING = "pending"
    STATUS_PROCESSING = "processing"
    STATUS_COMPLETED = "completed"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = [
        (STATUS_PENDING, "In attesa"),
        (STATUS_PROCESSING, "In elaborazione"),
        (STATUS_COMPLETED, "Completato"),
        (STATUS_FAILED, "Fallito"),
    ]
    AUTO_MATCH_SCORE_THRESHOLD = 80

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source_file = models.FileField(upload_to="hr/payslip_batches/")
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="payslip_batches")
    company = models.ForeignKey("clients.Company", on_delete=models.CASCADE, null=True, blank=True)
    resort = models.ForeignKey("resort.Resort", on_delete=models.CASCADE, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True)
    auto_match_strategy = models.CharField(
        max_length=50,
        default="fiscal_code",
        help_text="Strategia di auto-match: fiscal_code, username, email o regex su fiscal_code",
    )
    manifest_hint = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Regex per intercettare codice fiscale/ID nel nome file",
    )
    enable_ocr = models.BooleanField(
        default=True,
        help_text="Abilita OCR sui PDF singoli se il testo incorporato non contiene identificativi chiari",
    )
    ocr_languages = models.CharField(
        max_length=50,
        blank=True,
        default="ita+eng",
        help_text="Lingue da passare a Tesseract (es. ita+eng)",
    )
    manual_assignments = models.JSONField(blank=True, default=dict)
    total_items = models.PositiveIntegerField(default=0)
    matched_items = models.PositiveIntegerField(default=0)
    failed_items = models.PositiveIntegerField(default=0)
    processed_at = models.DateTimeField(null=True, blank=True)
    processing_duration_ms = models.PositiveIntegerField(default=0)
    auto_match_rate = models.FloatField(default=0)
    processing_log = models.JSONField(blank=True, default=list)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Batch {self.pk} ({self.status})"


    @transaction.atomic
    def process(self, actor=None):
        if self.status not in {self.STATUS_PENDING, self.STATUS_FAILED}:
            return self.processing_log

        started_at = timezone.now()

        self.total_items = 0
        self.matched_items = 0
        self.failed_items = 0
        self.processing_log = []
        self.unmatched_items.filter(resolved=False).delete()

        self.status = self.STATUS_PROCESSING
        self.save(update_fields=["status", "processing_log", "total_items", "matched_items", "failed_items"])
        HREventLog.record(
            event_type="payslip_batch_started",
            actor=actor,
            target=self,
            metadata={"batch_id": str(self.pk)},
        )

        try:
            with self.source_file.open("rb") as source_stream:
                payload = source_stream.read()
                if self.source_file.name.lower().endswith(".zip"):
                    self._process_zip_archive(io.BytesIO(payload))
                else:
                    self._process_single_pdf(payload)

            self.status = self.STATUS_COMPLETED
            self.processed_at = timezone.now()
            HREventLog.record(
                event_type="payslip_batch_completed",
                actor=actor,
                target=self,
                metadata={"batch_id": str(self.pk)},
            )
        except Exception as exc:  # pragma: no cover - safety net
            self.status = self.STATUS_FAILED
            self.processing_log.append({"status": "error", "detail": str(exc)})
            HREventLog.record(
                event_type="payslip_batch_failed",
                actor=actor,
                target=self,
                metadata={"batch_id": str(self.pk), "error": str(exc)},
            )
        finally:
            if started_at:
                elapsed = timezone.now() - started_at
                self.processing_duration_ms = int(elapsed.total_seconds() * 1000)
                self.auto_match_rate = (self.matched_items / self.total_items * 100) if self.total_items else 0
            self.save(
                update_fields=[
                    "status",
                    "processed_at",
                    "processing_duration_ms",
                    "auto_match_rate",
                    "processing_log",
                    "total_items",
                    "matched_items",
                    "failed_items",
                    "manifest_hint",
                ]
            )
        return self.processing_log


    def _process_zip_archive(self, source_stream):
        with ZipFile(source_stream) as archive:
            for filename in archive.namelist():
                if filename.endswith("/") or not filename.lower().endswith(".pdf"):
                    self.processing_log.append({"file": filename, "status": "skipped"})
                    continue

                self.total_items += 1
                pdf_bytes = archive.read(filename)

                try:
                    reader = PdfReader(io.BytesIO(pdf_bytes))
                    text = "".join(p.extract_text() or "" for p in reader.pages)
                except Exception as e:
                    self.processing_log.append({"file": filename, "status": "error", "detail": f"PDF parsing failed: {e}"})
                    text = "" # Fallback to empty text

                identifier_candidates = self._extract_identifiers_from_text(text, fallback="")
                identifier_source = "text"
                if not identifier_candidates:
                    identifier_candidates = [self._extract_identifier_from_name(filename)]
                    identifier_source = "filename"

                period_label, period_machine, period_confidence = self._extract_period_from_text(text)

                match_result = self._match_user_from_candidates(identifier_candidates)
                user = match_result["user"]
                score = match_result["score"]
                if user and score >= self.AUTO_MATCH_SCORE_THRESHOLD:
                    self._store_payslip(
                        user=user,
                        period_label=period_label,
                        period_machine=period_machine,
                        content=pdf_bytes,
                        metadata={
                            "source": "zip",
                            "identifier": identifier_candidates[0] if identifier_candidates else "",
                            "identifier_source": identifier_source,
                            "period_confidence": period_confidence,
                            "match_score": score,
                            "match_threshold": self.AUTO_MATCH_SCORE_THRESHOLD,
                            "candidate_scores": match_result["scores"],
                        },
                        auto_matched=True,
                    )
                else:
                    self._queue_unmatched(
                        identifier_candidates,
                        filename,
                        pdf_bytes,
                        reason="score_below_threshold",
                        metadata={
                            "identifier_source": identifier_source,
                            "period_label": period_label,
                            "period_machine": period_machine,
                            "period_confidence": period_confidence,
                            "match_score": score,
                            "match_threshold": self.AUTO_MATCH_SCORE_THRESHOLD,
                            "candidate_scores": match_result["scores"],
                        },
                    )

    def _process_single_pdf(self, pdf_bytes):
        reader = PdfReader(io.BytesIO(pdf_bytes))
        pdf_document = None
        if self.enable_ocr:
            try:
                import pypdfium2
                pdf_document = pypdfium2.PdfDocument(pdf_bytes)
            except Exception as exc:
                self.processing_log.append({"status": "ocr_unavailable", "detail": str(exc)})

        current_writer = None
        current_user = None
        current_identifier = ""
        current_period_label = ""
        current_period_machine = ""
        current_period_confidence = "fallback"
        current_match_score = 0
        current_candidate_scores = []
        current_text_sources = set()
        current_pages = []

        def flush_segment():
            nonlocal current_writer, current_user, current_identifier, current_pages, current_period_label, current_period_machine, current_period_confidence
            nonlocal current_match_score, current_candidate_scores, current_text_sources
            if not current_writer or not current_pages:
                return

            page_start = current_pages[0] + 1
            manual_data = self._resolve_manual_assignment_data(page_start, current_identifier)
            manual_override = False
            if manual_data:
                manual_user = manual_data.get("user")
                manual_period_label = manual_data.get("period_label")
                if manual_user:
                    current_user = manual_user
                    manual_override = True
                    current_match_score = max(current_match_score, self.AUTO_MATCH_SCORE_THRESHOLD)
                if manual_period_label:
                    current_period_label = manual_period_label
                    _, machine_label, _ = self._extract_period_from_text(f"{manual_period_label} 2000")
                    if machine_label:
                        current_period_machine = machine_label
                    manual_override = True

            buffer = io.BytesIO()
            current_writer.write(buffer)
            buffer.seek(0)
            content_bytes = buffer.getvalue()

            text_source = "mixed"
            if len(current_text_sources) == 1:
                text_source = next(iter(current_text_sources))
            elif not current_text_sources:
                text_source = "missing"

            metadata = {
                "source": "pdf_split",
                "page_indices": current_pages,
                "identifier": current_identifier,
                "identifier_source": "page_split",
                "period_confidence": current_period_confidence,
                "match_score": current_match_score,
                "match_threshold": self.AUTO_MATCH_SCORE_THRESHOLD,
                "candidate_scores": current_candidate_scores,
                "text_source": text_source,
                "manual_override": manual_override,
            }
            self.total_items += 1

            if current_user and current_match_score >= self.AUTO_MATCH_SCORE_THRESHOLD:
                self._store_payslip(
                    user=current_user,
                    period_label=current_period_label,
                    period_machine=current_period_machine,
                    content=content_bytes,
                    metadata=metadata,
                    auto_matched=True,
                )
            else:
                filename_base = Path(self.source_file.name).stem
                page_suffix = f"p{current_pages[0] + 1}" if current_pages else "segment"
                identifier_suffix = current_identifier or "segment"
                filename = f"{filename_base}-{identifier_suffix}-{page_suffix}.pdf"
                self._queue_unmatched(
                    [current_identifier],
                    filename,
                    content_bytes,
                    reason="score_below_threshold",
                    metadata={
                        "identifier_source": "page_split",
                        "period_label": current_period_label,
                        "period_machine": current_period_machine,
                        "period_confidence": current_period_confidence,
                        "match_score": current_match_score,
                        "match_threshold": self.AUTO_MATCH_SCORE_THRESHOLD,
                        "candidate_scores": current_candidate_scores,
                    },
                )

            current_writer, current_user, current_identifier, current_pages = None, None, "", []
            current_period_label, current_period_machine, current_period_confidence = "", "", "fallback"
            current_match_score, current_candidate_scores, current_text_sources = 0, [], set()

        for index, page in enumerate(reader.pages):
            text, text_source = self._extract_page_text(page, index, pdf_document)

            identifier_candidates = self._extract_identifiers_from_text(text, fallback=f"page-{index}")
            primary_identifier = self._select_primary_identifier(identifier_candidates)
            match_result = self._match_user_from_candidates(identifier_candidates)
            user = match_result["user"]
            score = match_result["score"]
            period_label, period_machine, period_confidence = self._extract_period_from_text(text)

            can_append = (
                current_writer is not None
                and current_user == user
                and (primary_identifier == current_identifier or not primary_identifier or not current_identifier)
                and (current_period_machine == period_machine or not current_period_machine or not period_machine)
            )

            if not can_append:
                flush_segment()

            if current_writer is None:
                current_writer = PdfWriter()
                current_user = user
                current_identifier = primary_identifier
                current_period_label, current_period_machine, current_period_confidence = period_label, period_machine, period_confidence
                current_match_score = score
                current_candidate_scores = match_result["scores"]
                current_text_sources = {text_source}
                current_pages = []
            else:
                current_text_sources.add(text_source)

            current_writer.add_page(page)
            current_pages.append(index)

        flush_segment()

    def preview_pdf_segments(self, pdf_bytes, progress_callback=None):
        return self._preview_pdf_segments(pdf_bytes, progress_callback=progress_callback)

    def _preview_pdf_segments(self, pdf_bytes, progress_callback=None, page_callback=None):
        reader = PdfReader(io.BytesIO(pdf_bytes))
        pdf_document = None
        if self.enable_ocr:
            try:
                import pypdfium2
                pdf_document = pypdfium2.PdfDocument(pdf_bytes)
            except Exception:
                pdf_document = None

        segments = []
        current_user = None
        current_identifier = ""
        current_period_label = ""
        current_period_machine = ""
        current_period_confidence = "fallback"
        current_match_score = 0
        current_candidate_scores = []
        current_text_sources = set()
        current_pages = []
        current_text_preview = ""

        def flush_segment():
            nonlocal current_user, current_identifier, current_pages, current_period_label, current_period_machine, current_period_confidence
            nonlocal current_match_score, current_candidate_scores, current_text_sources, current_text_preview
            if not current_pages:
                return

            text_source = "mixed"
            if len(current_text_sources) == 1:
                text_source = next(iter(current_text_sources))
            elif not current_text_sources:
                text_source = "missing"

            page_start = current_pages[0] + 1
            page_end = current_pages[-1] + 1
            manual_data = self._resolve_manual_assignment_data(page_start, current_identifier)
            manual_override = False
            manual_period_label = ""
            if manual_data:
                manual_user = manual_data.get("user")
                manual_period_label = manual_data.get("period_label") or ""
                if manual_user:
                    current_user = manual_user
                    manual_override = True
                    current_match_score = max(current_match_score, self.AUTO_MATCH_SCORE_THRESHOLD)
                if manual_period_label:
                    current_period_label = manual_period_label
                    _, machine_label, _ = self._extract_period_from_text(f"{manual_period_label} 2000")
                    if machine_label:
                        current_period_machine = machine_label
                    manual_override = True
            segments.append(
                {
                    "segment_key": f"p{page_start}",
                    "identifier": current_identifier,
                    "page_indices": current_pages,
                    "page_start": page_start,
                    "page_end": page_end,
                    "text_preview": current_text_preview,
                    "period_label": current_period_label,
                    "period_machine": current_period_machine,
                    "period_confidence": current_period_confidence,
                    "manual_period_label": manual_period_label,
                    "match_score": current_match_score,
                    "match_threshold": self.AUTO_MATCH_SCORE_THRESHOLD,
                    "candidate_scores": current_candidate_scores,
                    "text_source": text_source,
                    "auto_matched": bool(current_user and current_match_score >= self.AUTO_MATCH_SCORE_THRESHOLD),
                    "manual_assigned": manual_override,
                    "user": {
                        "id": current_user.id,
                        "username": current_user.username,
                        "full_name": current_user.get_full_name(),
                    }
                    if current_user
                    else None,
                }
            )

            current_user = None
            current_identifier = ""
            current_pages = []
            current_period_label = ""
            current_period_machine = ""
            current_period_confidence = "fallback"
            current_match_score = 0
            current_candidate_scores = []
            current_text_sources = set()
            current_text_preview = ""

        for index, page in enumerate(reader.pages):
            text, text_source = self._extract_page_text(page, index, pdf_document)
            if page_callback:
                page_callback(index, pdf_document)

            identifier_candidates = self._extract_identifiers_from_text(text, fallback=f"page-{index}")
            primary_identifier = self._select_primary_identifier(identifier_candidates)
            match_result = self._match_user_from_candidates(identifier_candidates)
            user = match_result["user"]
            score = match_result["score"]
            period_label, period_machine, period_confidence = self._extract_period_from_text(text)

            can_append = (
                current_pages
                and current_user == user
                and (primary_identifier == current_identifier or not primary_identifier or not current_identifier)
                and (current_period_machine == period_machine or not current_period_machine or not period_machine)
            )

            if not can_append:
                flush_segment()

            if not current_pages:
                current_user = user
                current_identifier = primary_identifier
                current_period_label = period_label
                current_period_machine = period_machine
                current_period_confidence = period_confidence
                current_match_score = score
                current_candidate_scores = match_result["scores"]
                current_text_sources = {text_source}
                current_text_preview = self._build_text_preview(text)
            else:
                current_text_sources.add(text_source)
                if not current_text_preview:
                    current_text_preview = self._build_text_preview(text)

            current_pages.append(index)
            if progress_callback:
                progress_callback(index + 1, len(reader.pages))

        flush_segment()
        return segments

    def preview_zip_segments(self, zip_bytes, max_files=5, max_pages=2):
        total_files = 0
        total_pdfs = 0
        auto_matched_count = 0
        samples = []
        errors = []

        with ZipFile(io.BytesIO(zip_bytes)) as archive:
            for filename in archive.namelist():
                if filename.endswith("/"):
                    continue
                total_files += 1
                if not filename.lower().endswith(".pdf"):
                    continue
                total_pdfs += 1
                if len(samples) >= max_files:
                    continue

                try:
                    pdf_bytes = archive.read(filename)
                    reader = PdfReader(io.BytesIO(pdf_bytes))
                    text_chunks = []
                    for page in reader.pages[:max_pages]:
                        page_text = page.extract_text() or ""
                        if page_text:
                            text_chunks.append(page_text)
                    text = "\n".join(text_chunks)
                    text_source = "pdf" if text.strip() else "missing"
                    text_preview = self._build_text_preview(text)

                    identifier_candidates = self._extract_identifiers_from_text(text, fallback="")
                    identifier_source = "text"
                    if not identifier_candidates:
                        identifier_candidates = [self._extract_identifier_from_name(filename)]
                        identifier_source = "filename"

                    match_result = self._match_user_from_candidates(identifier_candidates)
                    user = match_result["user"]
                    score = match_result["score"]
                    period_label, period_machine, period_confidence = self._extract_period_from_text(text)

                    auto_matched = bool(user and score >= self.AUTO_MATCH_SCORE_THRESHOLD)
                    if auto_matched:
                        auto_matched_count += 1

                    samples.append(
                        {
                            "file_name": filename,
                            "page_count": len(reader.pages),
                            "identifier": identifier_candidates[0] if identifier_candidates else "",
                            "identifier_source": identifier_source,
                            "period_label": period_label,
                            "period_machine": period_machine,
                            "period_confidence": period_confidence,
                            "match_score": score,
                            "match_threshold": self.AUTO_MATCH_SCORE_THRESHOLD,
                            "candidate_scores": match_result["scores"],
                            "text_source": text_source,
                            "text_preview": text_preview,
                            "auto_matched": auto_matched,
                            "manual_assigned": False,
                        }
                    )
                except Exception as exc:
                    errors.append({"file": filename, "detail": str(exc)})
                    samples.append(
                        {
                            "file_name": filename,
                            "page_count": 0,
                            "identifier": "",
                            "identifier_source": "error",
                            "period_label": "",
                            "period_machine": "",
                            "period_confidence": "fallback",
                            "match_score": 0,
                            "match_threshold": self.AUTO_MATCH_SCORE_THRESHOLD,
                            "candidate_scores": [],
                            "text_source": "missing",
                            "text_preview": "",
                            "auto_matched": False,
                            "manual_assigned": False,
                            "error": str(exc),
                        }
                    )

        sampled_count = len(samples)
        auto_match_rate = (auto_matched_count / sampled_count * 100) if sampled_count else 0
        summary = {
            "total_files": total_files,
            "total_pdfs": total_pdfs,
            "sampled_files": sampled_count,
            "auto_matched_count": auto_matched_count,
            "auto_match_rate": round(auto_match_rate, 1),
            "errors_count": len(errors),
            "sample_limit": max_files,
            "page_limit": max_pages,
        }
        return summary, samples, errors

    def _build_text_preview(self, text, limit=220):
        if not text:
            return ""
        compact = re.sub(r"\s+", " ", text).strip()
        if len(compact) <= limit:
            return compact
        clipped = compact[:limit].rsplit(" ", 1)[0]
        return f"{clipped}…"

    def _resolve_manual_assignment_data(self, page_start, identifier):
        assignments = self.manual_assignments or {}
        segment_assignments = assignments.get("segments") if isinstance(assignments, dict) else {}
        if not isinstance(segment_assignments, dict):
            segment_assignments = {}
        data = segment_assignments.get(f"p{page_start}")
        if not data and isinstance(assignments, dict):
            identifier_map = assignments.get("identifiers")
            if isinstance(identifier_map, dict) and identifier:
                data = identifier_map.get(identifier)
        if not data:
            return None
        if isinstance(data, dict):
            user_id = data.get("user_id") or data.get("user")
            period_label = data.get("period_label") or ""
        else:
            user_id = data
            period_label = ""
        if not user_id and not period_label:
            return None
        return {
            "user": self._get_user_in_scope(user_id) if user_id else None,
            "period_label": period_label,
        }

    def _get_user_in_scope(self, user_id):
        User = settings.AUTH_USER_MODEL  # type: ignore
        from django.apps import apps

        UserModel = apps.get_model(User)
        scope_filters = {"id": user_id}
        if self.company_id and hasattr(UserModel, "company_id"):
            scope_filters["company_id"] = self.company_id
        if self.resort_id and hasattr(UserModel, "resort_id"):
            scope_filters["resort_id"] = self.resort_id
        return UserModel.objects.filter(**scope_filters).first()

    def _extract_period_from_text(self, text):
        """
        Extracts the payslip period (month and year) from text content.
        Returns a human-readable label ("Mese Anno"), a machine-readable label ("ANNO_MM"),
        and a confidence label ("high" or "fallback").
        """
        month_map = {
            "gennaio": "01", "febbraio": "02", "marzo": "03", "aprile": "04",
            "maggio": "05", "giugno": "06", "luglio": "07", "agosto": "08",
            "settembre": "09", "ottobre": "10", "novembre": "11", "dicembre": "12",
            "gen": "01", "feb": "02", "mar": "03", "apr": "04", "mag": "05",
            "giu": "06", "lug": "07", "ago": "08", "set": "09", "ott": "10",
            "nov": "11", "dic": "12",
        }
        month_regex = r"(?P<month>{})\s+(?P<year>\d{{4}})".format("|".join(month_map.keys()))
        match = re.search(month_regex, text, re.IGNORECASE)

        if match:
            month_name = match.group("month").lower()
            year = match.group("year")
            month_number = month_map.get(month_name)
            if month_number:
                human_label = f"{month_name.capitalize()} {year}"
                machine_label = f"{year}_{month_number}"
                return human_label, machine_label, "high"

        numeric_patterns = [
            r"(?P<year>20\d{2})[\/\-_\. ](?P<month>0?[1-9]|1[0-2])",
            r"(?P<month>0?[1-9]|1[0-2])[\/\-_\. ](?P<year>20\d{2})",
        ]
        for pattern in numeric_patterns:
            match = re.search(pattern, text)
            if match:
                year = match.group("year")
                month_number = match.group("month").zfill(2)
                human_label = f"{month_number}/{year}"
                machine_label = f"{year}_{month_number}"
                return human_label, machine_label, "high"

        created_at = self.created_at or timezone.now()
        human_fallback = created_at.strftime("%B %Y")
        machine_fallback = created_at.strftime("%Y_%m")
        return human_fallback, machine_fallback, "fallback"

    def _extract_identifier_from_name(self, filename):
        identifier = Path(filename).stem
        if self.manifest_hint:
            regex = re.compile(self.manifest_hint)
            match = regex.search(filename) or regex.search(identifier)
            if match:
                if match.groupdict():
                    identifier = next((v for k, v in match.groupdict().items() if v), identifier)
                elif match.groups():
                    identifier = match.group(1)
                return identifier
        if self.auto_match_strategy == "fiscal_code":
            fiscal_code_regex = re.compile(r"[A-Z]{6}\d{2}[A-Z]\d{2}[A-Z]\d{3}[A-Z]", re.IGNORECASE)
            match = fiscal_code_regex.search(filename)
            return match.group(0) if match else ""
        return identifier

    def _select_primary_identifier(self, candidates):
        fiscal_code_regex = re.compile(r"[A-Z]{6}\d{2}[A-Z]\d{2}[A-Z]\d{3}[A-Z]", re.IGNORECASE)
        for candidate in candidates:
            if fiscal_code_regex.fullmatch(candidate.strip()):
                return candidate.strip()
        prioritized = self._prioritize_identifiers(candidates)
        return prioritized[0].strip() if prioritized else ""

    def _extract_identifiers_from_text(self, text, fallback=""):
        candidates = []
        if self.manifest_hint:
            regex = re.compile(self.manifest_hint, re.IGNORECASE)
            for match in regex.finditer(text):
                if match.groupdict():
                    candidates.extend([v for v in match.groupdict().values() if v])
                elif match.groups():
                    candidates.extend([g for g in match.groups() if g])
                else:
                    candidates.append(match.group(0))

        fiscal_code_regex = re.compile(r"[A-Z]{6}\d{2}[A-Z]\d{2}[A-Z]\d{3}[A-Z]", re.IGNORECASE)
        fiscal_candidates = fiscal_code_regex.findall(text)
        candidates.extend(fiscal_candidates)

        if not fiscal_candidates and self.auto_match_strategy != "fiscal_code":
            name_regex = re.compile(r"([A-Z][a-zA-Z']+\s+[A-Z][a-zA-Z']+)")
            candidates.extend(name_regex.findall(text))

            uppercase_name_regex = re.compile(r"\b([A-Z]{2,}\s+[A-Z]{2,})\b")
            candidates.extend(uppercase_name_regex.findall(text))

        if fallback:
            candidates.append(fallback)

        return self._dedupe_identifiers(candidates)

    def _dedupe_identifiers(self, candidates):
        seen = set()
        unique = []
        for candidate in candidates:
            normalized = self._normalize_identifier(candidate)
            if self._is_noise_identifier(normalized):
                continue
            if normalized and normalized not in seen:
                seen.add(normalized)
                unique.append(normalized)
        return unique

    def _normalize_identifier(self, identifier):
        normalized = (identifier or "").strip()
        normalized = re.sub(r"\s+", " ", normalized)
        return normalized

    def _is_noise_identifier(self, identifier):
        if not identifier:
            return True
        tokens = identifier.upper().split()
        stop_words = {
            "SOCIETA",
            "SRL",
            "SPA",
            "INAIL",
            "INPS",
            "AZIENDA",
            "FILIALE",
            "DIPENDENTE",
            "QUALIFICA",
            "POSIZIONE",
            "RETRIBUZIONE",
        }
        return any(token in stop_words for token in tokens)

    def _prioritize_identifiers(self, identifiers):
        scored = []
        for identifier in identifiers or []:
            normalized = self._normalize_identifier(identifier)
            if not normalized:
                continue
            scored.append((self._identifier_score(normalized), normalized))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [identifier for _, identifier in scored]

    def _identifier_score(self, identifier):
        if re.fullmatch(r"[A-Z]{6}\d{2}[A-Z]\d{2}[A-Z]\d{3}[A-Z]", identifier, re.IGNORECASE):
            return 100
        if "@" in identifier:
            return 90
        if re.fullmatch(r"[A-Z][a-zA-Z']+\s+[A-Z][a-zA-Z']+", identifier):
            return 70
        if re.fullmatch(r"[A-Z]{2,}\s+[A-Z]{2,}", identifier):
            return 70
        if identifier.lower().startswith("page-"):
            return 10
        return 80

    def _score_identifier(self, identifier):
        return self._identifier_score(identifier)

    def _match_user_from_candidates(self, identifiers):
        best_match = {
            "user": None,
            "score": 0,
            "identifier": "",
            "scores": [],
        }
        for identifier in self._prioritize_identifiers(identifiers):
            user = self._match_user(identifier)
            score = self._score_identifier(identifier)
            best_match["scores"].append(
                {
                    "identifier": identifier,
                    "score": score,
                    "matched": bool(user),
                }
            )
            if user and score > best_match["score"]:
                best_match.update({"user": user, "score": score, "identifier": identifier})
        return best_match

    def _match_user(self, identifier):
        identifier = (identifier or "").strip()
        if not identifier:
            return None

        User = settings.AUTH_USER_MODEL  # type: ignore
        from django.apps import apps

        UserModel = apps.get_model(User)
        user_fields = {field.name for field in UserModel._meta.get_fields()}
        fiscal_fields = [field for field in ["fiscal_code", "tax_code", "codice_fiscale"] if field in user_fields]
        filters = []
        scope_filters = {}

        if self.company_id and hasattr(UserModel, "company_id"):
            scope_filters["company_id"] = self.company_id
        if self.resort_id and hasattr(UserModel, "resort_id"):
            scope_filters["resort_id"] = self.resort_id

        if self.auto_match_strategy == "fiscal_code":
            for field in fiscal_fields:
                filters.append({field: identifier})
        elif self.auto_match_strategy == "email":
            filters.append({"email__iexact": identifier})
        elif self.auto_match_strategy == "username":
            filters.append({"username": identifier})
        else:
            filters.extend([{"username": identifier}, {"email__iexact": identifier}])

        if self.manifest_hint:
            regex = re.compile(self.manifest_hint)
            for field in fiscal_fields:
                filters.append({field: identifier})
                if regex.match(identifier):
                    filters.insert(0, {field: identifier})

        if not filters:
            filters = [{"username": identifier}, {"email__iexact": identifier}]

        for filter_kwargs in filters:
            query_kwargs = {**filter_kwargs, **scope_filters}
            user = UserModel.objects.filter(**query_kwargs).first()
            if user:
                return user

        user = self._match_user_by_name(UserModel, identifier, scope_filters)
        if user:
            return user
        return None

    def _match_user_by_name(self, user_model, identifier, scope_filters):
        parts = [part for part in identifier.split(" ") if part]
        if len(parts) != 2:
            return None

        first_name, last_name = parts
        if not hasattr(user_model, "first_name") or not hasattr(user_model, "last_name"):
            return None

        return user_model.objects.filter(
            first_name__iexact=first_name,
            last_name__iexact=last_name,
            **scope_filters,
        ).first()

    def _normalize_period_for_filename(self, period_machine):
        if not period_machine:
            created_at = self.created_at or timezone.now()
            return created_at.strftime("%Y-%m")

        match = re.search(r"(20\d{2})[_-]?(0[1-9]|1[0-2])", period_machine)
        if match:
            return f"{match.group(1)}-{match.group(2)}"

        return str(period_machine).replace("_", "-")

    def _build_payslip_name(self, user, period_label=None):
        """
        Generates a filename in the format CF_ANNO-MESE.pdf.
        """
        fiscal_code = (getattr(user, "fiscal_code", "") or getattr(user, "tax_code", "") or "").upper()
        if not fiscal_code:
            fiscal_code = (getattr(user, "username", "") or "NO_CF").upper()

        # Use the provided period label (expected YYYY_MM), or fall back to the batch creation date
        created_at = self.created_at or timezone.now()
        year_month = period_label or created_at.strftime("%Y_%m")
        normalized_period = self._normalize_period_for_filename(year_month)

        # Construct the final filename
        base_name = f"{fiscal_code}_{normalized_period}"
        filename = f"{base_name}.pdf"

        return filename


    def _build_unmatched_name(self, original_name, preferred_stem=""):
        """Return a bounded-length basename for unmatched items."""

        base_name = Path(original_name or "").name
        stem_source = preferred_stem or Path(base_name).stem
        stem = slugify(stem_source) or "payslip"
        ext = Path(base_name).suffix or ".pdf"
        unique_token = uuid.uuid4().hex[:8]

        max_length = 70
        budget = max_length - len(unique_token) - len(ext) - 1
        safe_stem = stem[: budget if budget > 0 else 0]

        filename = "-".join(part for part in [unique_token, safe_stem] if part)
        return f"{filename}{ext}"

    def _select_unmatched_label(self, identifiers):
        prioritized = self._prioritize_identifiers(identifiers)
        for identifier in prioritized:
            if identifier.lower().startswith("page-"):
                continue
            return identifier
        return ""

    def _fallback_identifier_from_filename(self, filename):
        stem = Path(filename or "").stem
        cleaned = re.sub(r"[-_]?page-\d+", "", stem, flags=re.IGNORECASE)
        cleaned = re.sub(r"[-_]?p\d+$", "", cleaned, flags=re.IGNORECASE)
        cleaned = cleaned.strip("-_")
        normalized = cleaned.replace("-", " ").replace("_", " ").strip()
        return normalized or stem

    def _queue_unmatched(self, identifiers, filename, content_bytes, reason="", metadata=None):
        identifier = self._select_unmatched_label(identifiers)
        if not identifier:
            identifier = self._fallback_identifier_from_filename(filename)
        unmatched = PayslipUnmatched(
            batch=self,
            identifier=identifier,
            company=self.company,
            resort=self.resort,
        )
        unmatched.file.save(
            self._build_unmatched_name(filename, preferred_stem=identifier),
            ContentFile(content_bytes),
            save=False,
        )
        unmatched.save()

        self.failed_items += 1
        self.processing_log.append(
            {
                "file": filename,
                "status": "unmatched",
                "identifier": identifier,
                "unmatched_id": str(unmatched.id),
                "reason": reason,
                "metadata": metadata or {},
            }
        )

    def _store_payslip(self, user, period_label, period_machine, content, metadata=None, auto_matched=True):
        payslip_content = ContentFile(content)
        payslip = Payslip(
            user=user,
            batch=self,
            company=self.company or getattr(user, "company", None),
            resort=self.resort or getattr(user, "resort", None),
            auto_matched=auto_matched,
            status=Payslip.STATUS_AVAILABLE,
            metadata=metadata or {},
            period_label=period_label,
        )

        filename = self._build_payslip_name(user, period_machine)
        available_name = payslip.file.storage.get_available_name(filename)
        payslip.file.save(available_name, payslip_content, save=False)
        payslip.save()

        try:
            from .services import notify_payslip_ready
            notify_payslip_ready(user, payslip)
        except Exception:
            pass

        self.matched_items += 1
        match_score = (metadata or {}).get("match_score")
        match_threshold = (metadata or {}).get("match_threshold")
        self.processing_log.append(
            {
                "file": filename,
                "status": "assigned",
                "user": user.username,
                "match_score": match_score,
                "match_threshold": match_threshold,
            }
        )


    def _perform_ocr(self, pdf_document, page_index):
        try:
            import shutil
            if not shutil.which("tesseract"):
                self.processing_log.append(
                    {"status": "ocr_unavailable", "page": page_index, "detail": "tesseract_not_installed"}
                )
                return ""
            import pytesseract

            page = pdf_document.get_page(page_index)
            pil_image = page.render(scale=2).to_pil()
            return pytesseract.image_to_string(pil_image, lang=self.ocr_languages or "ita+eng")
        except Exception as exc:  # pragma: no cover - optional dependency/runner
            self.processing_log.append(
                {"status": "ocr_error", "page": page_index, "detail": str(exc)}
            )
        return ""

    def _extract_page_text(self, page, page_index, pdf_document=None):
        text = ""
        try:
            text = page.extract_text() or ""
        except Exception as exc:
            self.processing_log.append(
                {"page": page_index, "status": "error", "detail": f"PDF page parsing failed: {exc}"}
            )
        text = text.strip()

        if self.enable_ocr and pdf_document and not text:
            ocr_text = self._perform_ocr(pdf_document, page_index)
            if ocr_text:
                return ocr_text.strip(), "ocr"
            return "", "missing"

        if text:
            return text, "embedded"
        return "", "missing"


class PayslipBatchPreview(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="payslip_batch_previews",
    )
    source_filename = models.CharField(max_length=255, blank=True, default="")
    source_checksum = models.CharField(max_length=64, blank=True, default="")
    manual_assignments = models.JSONField(blank=True, default=dict)
    locked_at = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Preview {self.pk}"


class PayslipPreviewJob(models.Model):
    SEGMENT_PREVIEW_UNAVAILABLE = "segment_preview_unavailable"
    STATUS_QUEUED = "queued"
    STATUS_RUNNING = "running"
    STATUS_COMPLETED = "completed"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = [
        (STATUS_QUEUED, "In coda"),
        (STATUS_RUNNING, "In esecuzione"),
        (STATUS_COMPLETED, "Completata"),
        (STATUS_FAILED, "Fallita"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="payslip_preview_jobs",
    )
    source_file = models.FileField(upload_to="hr/payslip_previews/", max_length=255)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_QUEUED, db_index=True)
    progress_percent = models.PositiveIntegerField(default=0)
    total_items = models.PositiveIntegerField(default=0)
    processed_items = models.PositiveIntegerField(default=0)
    metadata = models.JSONField(blank=True, default=dict)
    preview_payload = models.JSONField(blank=True, default=dict)
    error_message = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Preview job {self.pk} ({self.status})"

    def _append_event(self, message, level="info"):
        payload = self.preview_payload or {}
        events = payload.get("events", [])
        events.append(
            {
                "message": message,
                "level": level,
                "timestamp": timezone.now().isoformat(),
            }
        )
        payload["events"] = events[-20:]
        self.preview_payload = payload
        self.save(update_fields=["preview_payload", "updated_at"])

    def _add_scan_page(self, image_bytes, page_index):
        if not image_bytes:
            return
        page = PayslipPreviewPage.objects.create(
            preview_job=self,
            page_index=page_index,
        )
        page.image.save(f"preview_{self.pk}_p{page_index}.png", ContentFile(image_bytes), save=True)
        payload = self.preview_payload or {}
        scan_pages = payload.get("scan_pages", [])
        scan_pages.append(
            {
                "page_index": page_index,
                "image_url": page.image.url,
            }
        )
        payload["scan_pages"] = scan_pages
        self.preview_payload = payload
        self.save(update_fields=["preview_payload", "updated_at"])

    def _default_capabilities(self):
        payload = self.preview_payload or {}
        capabilities = payload.get("capabilities") if isinstance(payload, dict) else {}
        if not isinstance(capabilities, dict):
            capabilities = {}
        return {
            "schema_version": "v2",
            "mode": "async",
            "stream_available": True,
            "polling_available": True,
            "ocr_enabled": bool((self.metadata or {}).get("enable_ocr")),
            "ocr_available": capabilities.get("ocr_available"),
            "rendering_available": bool(payload.get("scan_pages")),
        }

    def build_preview_payload(self):
        payload = self.preview_payload or {}
        if not isinstance(payload, dict):
            return {}

        base_capabilities = payload.get("capabilities") if isinstance(payload.get("capabilities"), dict) else {}
        normalized_payload = {
            **payload,
            "capabilities": {
                **base_capabilities,
                "schema_version": "v2",
            },
        }

        segments = normalized_payload.get("segments")
        if not isinstance(segments, list):
            return normalized_payload

        scan_pages = normalized_payload.get("scan_pages")
        page_map = {}
        if isinstance(scan_pages, list):
            for page in scan_pages:
                page_index = page.get("page_index") if isinstance(page, dict) else None
                if isinstance(page_index, int):
                    page_map[page_index] = page

        enriched_segments = []
        for segment in segments:
            if not isinstance(segment, dict):
                enriched_segments.append(segment)
                continue

            has_existing_preview_pages = isinstance(segment.get("preview_pages"), list)
            if has_existing_preview_pages:
                preview_pages = segment.get("preview_pages") or []
            else:
                page_start = segment.get("page_start")
                page_end = segment.get("page_end")
                preview_pages = []
                if isinstance(page_start, int) and isinstance(page_end, int) and page_start <= page_end:
                    for page_idx in range(page_start, page_end + 1):
                        if page_idx in page_map:
                            preview_pages.append(page_map[page_idx])

            preview_available = bool(preview_pages)
            segment_payload = {
                **segment,
                "preview_pages": preview_pages,
                "preview_available": preview_available,
            }
            if not preview_available and segment_payload.get("error") in (None, "") and not segment_payload.get("preview_error_code"):
                segment_payload["preview_error_code"] = self.SEGMENT_PREVIEW_UNAVAILABLE

            enriched_segments.append(segment_payload)

        return {
            **normalized_payload,
            "segments": enriched_segments,
        }

    def start_processing(self):
        try:
            from .tasks import process_payslip_preview_job

            process_payslip_preview_job.delay(str(self.pk))
        except Exception:
            self._run_processing()

    def _run_processing(self):
        self.status = self.STATUS_RUNNING
        self.error_message = ""
        self.progress_percent = 0
        self.processed_items = 0
        self.preview_payload = {"capabilities": self._default_capabilities()}
        self.save(
            update_fields=[
                "status",
                "error_message",
                "progress_percent",
                "processed_items",
                "preview_payload",
                "updated_at",
            ]
        )
        self._append_event("Preview avviata.")
        HREventLog.record(
            event_type="preview_started",
            actor=self.created_by,
            target=self,
            metadata={"preview_job_id": str(self.pk)},
        )

        def progress_callback(processed, total):
            total_value = max(total, 1)
            progress = int(round((processed / total_value) * 100))
            self.processed_items = processed
            self.total_items = total_value
            self.progress_percent = min(100, max(0, progress))
            self.save(update_fields=["processed_items", "total_items", "progress_percent", "updated_at"])

        try:
            filename = (self.source_file.name or "").lower()
            with self.source_file.open("rb") as source_handle:
                payload = source_handle.read()

            job_meta = self.metadata or {}
            batch = PayslipBatch(
                enable_ocr=job_meta.get("enable_ocr", False),
                ocr_languages=job_meta.get("ocr_languages") or "ita+eng",
                auto_match_strategy=job_meta.get("auto_match_strategy") or "fiscal_code",
                manifest_hint=job_meta.get("manifest_hint") or "",
                company_id=getattr(self.created_by, "company_id", None),
                resort_id=getattr(self.created_by, "resort_id", None),
            )

            if filename.endswith(".zip"):
                self._append_event("Analisi ZIP in corso.")
                total_pdfs = 0
                with ZipFile(io.BytesIO(payload)) as archive:
                    for name in archive.namelist():
                        if name.lower().endswith(".pdf") and not name.endswith("/"):
                            total_pdfs += 1
                self.total_items = total_pdfs
                self.save(update_fields=["total_items", "updated_at"])
                summary, samples, errors = batch.preview_zip_segments(
                    payload,
                    max_files=total_pdfs,
                    max_pages=2,
                    progress_callback=progress_callback,
                )
                self.preview_payload = {
                    "file_name": self.source_file.name,
                    "preview_type": "zip",
                    "summary": summary,
                    "segments": samples,
                    "errors": errors,
                    "total_segments": len(samples),
                    "events": (self.preview_payload or {}).get("events", []),
                    "capabilities": {**self._default_capabilities(), "rendering_available": False, "ocr_available": False},
                }
            elif filename.endswith(".pdf"):
                reader = PdfReader(io.BytesIO(payload))
                self.total_items = len(reader.pages)
                self.save(update_fields=["total_items", "updated_at"])
                pdfium_spec = importlib.util.find_spec("pypdfium2")
                pdfium_available = pdfium_spec is not None
                self.preview_payload = {
                    "ocr_enabled": bool(job_meta.get("enable_ocr")),
                    "ocr_available": pdfium_available,
                    "events": (self.preview_payload or {}).get("events", []),
                    "capabilities": {**self._default_capabilities(), "rendering_available": False, "ocr_available": pdfium_available},
                }
                self.save(update_fields=["preview_payload", "updated_at"])
                if job_meta.get("enable_ocr"):
                    if pdfium_available:
                        self._append_event("OCR disponibile: rendering pagine attivo.")
                    else:
                        self._append_event("OCR non disponibile: pypdfium2 non presente.", level="warning")
                if pdfium_available:
                    import pypdfium2
                    pdf_document = pypdfium2.PdfDocument(payload)
                else:
                    pdf_document = None

                def page_callback(page_index, document):
                    if not document or not pdfium_available:
                        return
                    page = document.get_page(page_index)
                    image = page.render_topil(scale=1)
                    image_buffer = io.BytesIO()
                    image.save(image_buffer, format="PNG")
                    self._add_scan_page(image_buffer.getvalue(), page_index + 1)
                    page.close()

                segments = batch._preview_pdf_segments(
                    payload,
                    progress_callback=progress_callback,
                    page_callback=page_callback,
                )
                if pdf_document:
                    pdf_document.close()
                payload_preview = self.preview_payload or {}
                self.preview_payload = {
                    "file_name": self.source_file.name,
                    "preview_type": "pdf",
                    "segments": segments,
                    "total_segments": len(segments),
                    "scan_pages": payload_preview.get("scan_pages", []),
                    "ocr_enabled": payload_preview.get("ocr_enabled"),
                    "ocr_available": payload_preview.get("ocr_available"),
                    "events": payload_preview.get("events", []),
                    "capabilities": {
                        **self._default_capabilities(),
                        "ocr_available": payload_preview.get("ocr_available"),
                        "rendering_available": bool(payload_preview.get("scan_pages", [])),
                    },
                }
            else:
                raise ValueError("L'anteprima è disponibile per PDF singoli o ZIP.")

            self._append_event("Preview completata.")
            HREventLog.record(
                event_type="preview_completed",
                actor=self.created_by,
                target=self,
                metadata={"preview_job_id": str(self.pk), "total_items": self.total_items},
            )
            self.status = self.STATUS_COMPLETED
            self.progress_percent = 100
            self.save(update_fields=["status", "preview_payload", "progress_percent", "updated_at"])
        except Exception as exc:
            self._append_event("Preview fallita.", level="error")
            HREventLog.record(
                event_type="preview_failed",
                actor=self.created_by,
                target=self,
                metadata={"preview_job_id": str(self.pk), "error": str(exc)[:500]},
            )
            self.status = self.STATUS_FAILED
            self.error_message = str(exc)
            self.save(update_fields=["status", "error_message", "updated_at"])


class PayslipPreviewPage(models.Model):
    preview_job = models.ForeignKey(
        PayslipPreviewJob,
        on_delete=models.CASCADE,
        related_name="pages",
    )
    page_index = models.PositiveIntegerField()
    image = models.FileField(upload_to="hr/payslip_previews/pages/", max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["page_index"]
        unique_together = ("preview_job", "page_index")

    def __str__(self):
        return f"Preview page {self.page_index} for {self.preview_job_id}"


class Payslip(models.Model):
    STATUS_PENDING = "pending"
    STATUS_AVAILABLE = "available"
    STATUS_REQUIRES_REVIEW = "requires_review"
    STATUS_CHOICES = [
        (STATUS_PENDING, "In attesa"),
        (STATUS_AVAILABLE, "Disponibile"),
        (STATUS_REQUIRES_REVIEW, "Da revisionare"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="payslips")
    batch = models.ForeignKey(PayslipBatch, on_delete=models.CASCADE, related_name="payslips")
    company = models.ForeignKey("clients.Company", on_delete=models.CASCADE, null=True, blank=True)
    resort = models.ForeignKey("resort.Resort", on_delete=models.CASCADE, null=True, blank=True)
    period_label = models.CharField(max_length=50, blank=True, default="")
    file = models.FileField(upload_to="hr/payslips/", max_length=255)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True)
    auto_matched = models.BooleanField(default=False)
    metadata = models.JSONField(blank=True, default=dict)
    downloaded_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status", "created_at"])]

    def __str__(self):
        return f"Payslip {self.period_label or ''} for {self.user.username}"


class PayslipEmailRecipient(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(max_length=255, db_index=True)
    company = models.ForeignKey("clients.Company", on_delete=models.CASCADE, null=True, blank=True)
    resort = models.ForeignKey("resort.Resort", on_delete=models.CASCADE, null=True, blank=True)
    used_count = models.PositiveIntegerField(default=0)
    last_used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-last_used_at", "-created_at"]
        unique_together = ("email", "company", "resort")
        indexes = [
            models.Index(fields=["email", "company", "resort"]),
        ]

    def __str__(self):
        scope = []
        if self.company_id:
            scope.append(f"company={self.company_id}")
        if self.resort_id:
            scope.append(f"resort={self.resort_id}")
        return f"{self.email} ({', '.join(scope)})" if scope else self.email

class HREventLog(models.Model):
    EVENT_CHOICES = [
        ("document_ack", "ACK Documento"),
        ("payslip_download", "Download Busta Paga"),
        ("payslip_resolved", "Busta Paga assegnata manualmente"),
        ("payslip_email_sent", "Invio busta paga via email"),
        ("payslip_email_failed", "Errore invio busta paga via email"),
        ("payslip_notified", "Notifica disponibilità busta paga"),
        ("payslip_batch_started", "Batch buste paga avviato"),
        ("payslip_batch_completed", "Batch buste paga completato"),
        ("payslip_batch_failed", "Batch buste paga fallito"),
        ("payslip_batch_created", "Batch buste paga creato"),
        ("notification_delivered", "Notifica consegnata"),
        ("notification_published", "Notifica pubblicata"),
        ("notification_archived", "Notifica archiviata"),
        ("notification_delivery_failed", "Notifica fallita"),
        ("notification_created", "Notifica creata"),
        ("notification_updated", "Notifica aggiornata"),
        ("notification_status_changed", "Stato notifica aggiornato"),
        ("ticket_escalated", "Ticket escalato"),
        ("ticket_closed", "Ticket chiuso"),
        ("ticket_assigned", "Ticket assegnato"),
        ("ticket_created", "Ticket creato"),
        ("ticket_message", "Messaggio ticket"),
        ("preview_started", "Preview buste paga avviata"),
        ("preview_completed", "Preview buste paga completata"),
        ("preview_failed", "Preview buste paga fallita"),
        ("preview_confirmed", "Preview buste paga confermata"),
        ("preview_fallback_polling", "Preview passata a polling fallback"),
        ("preview_incident_ack", "Incidente preview preso in carico"),
        ("preview_incident_resolved", "Incidente preview risolto"),
        ("preview_incident_action_completed", "Azione correttiva incidente completata"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_type = models.CharField(max_length=64, choices=EVENT_CHOICES)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    target_model = models.CharField(max_length=128)
    target_id = models.CharField(max_length=128)
    metadata = models.JSONField(blank=True, default=dict)
    company = models.ForeignKey("clients.Company", on_delete=models.SET_NULL, null=True, blank=True)
    resort = models.ForeignKey("resort.Resort", on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["event_type", "created_at"]),
            models.Index(fields=["company", "resort", "created_at"]),
        ]

    def __str__(self):
        return f"{self.event_type} on {self.target_model}:{self.target_id}"

    @classmethod
    def record(cls, event_type, actor=None, target=None, metadata=None):
        if not target:
            return None
        company = getattr(target, "company", None)
        resort = getattr(target, "resort", None)
        if not company and actor is not None:
            company = getattr(actor, "company", None)
        if not resort and actor is not None:
            resort = getattr(actor, "resort", None)
        target_model = target.__class__.__name__
        target_id = getattr(target, "pk", None) or getattr(target, "id", "")
        return cls.objects.create(
            event_type=event_type,
            actor=actor if actor and getattr(actor, "is_authenticated", False) else None,
            target_model=target_model,
            target_id=str(target_id),
            metadata=metadata or {},
            company=company if hasattr(company, "id") else None,
            resort=resort if hasattr(resort, "id") else None,
        )


class ListeningTicket(models.Model):
    PRIORITY_CHOICES = [
        ("low", "Bassa"),
        ("normal", "Normale"),
        ("high", "Alta"),
    ]
    STATUS_CHOICES = [
        ("new", "Nuovo"),
        ("in_progress", "In lavorazione"),
        ("closed", "Chiuso"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="listening_tickets")
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="listening_tickets_assigned",
    )
    company = models.ForeignKey("clients.Company", on_delete=models.CASCADE, null=True, blank=True)
    resort = models.ForeignKey("resort.Resort", on_delete=models.CASCADE, null=True, blank=True)
    subject = models.CharField(max_length=255)
    message = models.TextField()
    is_anonymous = models.BooleanField(default=False)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default="normal")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="new", db_index=True)
    sentiment = models.CharField(max_length=20, blank=True, default="")
    sla_hours = models.PositiveIntegerField(default=72, help_text="SLA orario per la gestione del ticket")
    due_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    tags = models.JSONField(blank=True, default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status", "priority", "created_at"])]

    def __str__(self):
        return self.subject

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        if is_new and not self.due_at:
            base = timezone.now()
            self.due_at = base + timezone.timedelta(hours=self.sla_hours)
        if self.status == "closed" and not self.closed_at:
            self.closed_at = timezone.now()
        super().save(*args, **kwargs)


class ListeningTicketMessage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ticket = models.ForeignKey(ListeningTicket, on_delete=models.CASCADE, related_name="messages")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="listening_messages")
    body = models.TextField()
    is_internal = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [models.Index(fields=["ticket", "created_at"])]

    def __str__(self):
        return f"Messaggio ticket {self.ticket_id}"
class PayslipUnmatched(models.Model):
    STATUS_TO_ASSIGN = "to_assign"
    STATUS_RESOLVED = "resolved"
    STATUS_CHOICES = [
        (STATUS_TO_ASSIGN, "DA ASSEGNARE"),
        (STATUS_RESOLVED, "ASSEGNATO"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    batch = models.ForeignKey("PayslipBatch", on_delete=models.CASCADE, related_name="unmatched_items")
    identifier = models.CharField(max_length=255, blank=True, default="")
    file = models.FileField(upload_to="hr/payslips/unmatched/", max_length=255)
    company = models.ForeignKey("clients.Company", on_delete=models.CASCADE, null=True, blank=True)
    resort = models.ForeignKey("resort.Resort", on_delete=models.CASCADE, null=True, blank=True)
    resolved = models.BooleanField(default=False)
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default=STATUS_TO_ASSIGN, db_index=True)
    resolved_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="resolved_payslip_unmatched"
    )
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="resolved_payslip_unmatched_by"
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["resolved", "created_at"]),
        ]

    def mark_resolved(self, user, resolved_by=None, period_label=""):
        from django.utils import timezone

        if self.resolved:
            return None

        content_bytes = self._load_unmatched_content()

        # Extract period from the PDF content
        text_parts = []
        try:
            reader = PdfReader(io.BytesIO(content_bytes))
            for page in reader.pages:
                try:
                    text_parts.append(page.extract_text() or "")
                except Exception:
                    continue
        except Exception:
            text_parts = []
        text = "".join(text_parts)
        extracted_period_label, period_machine, period_confidence = self.batch._extract_period_from_text(text)

        final_period_label = period_label or extracted_period_label

        payslip = Payslip(
            user=user,
            batch=self.batch,
            company=self.batch.company or getattr(user, "company", None) or self.company,
            resort=self.batch.resort or getattr(user, "resort", None) or self.resort,
            auto_matched=False,
            status=Payslip.STATUS_AVAILABLE,
            metadata={
                "source": "manual_resolve",
                "identifier": self.identifier,
                "period_confidence": period_confidence,
            },
            period_label=final_period_label,
        )

        content = ContentFile(content_bytes)
        filename = self.batch._build_payslip_name(user, period_machine)
        available_name = payslip.file.storage.get_available_name(filename)
        payslip.file.save(available_name, content, save=False)
        payslip.save()

        try:
            from .services import notify_payslip_ready
            notify_payslip_ready(user, payslip)
        except Exception:
            pass

        self.resolved = True
        self.resolved_to = user
        self.resolved_by = resolved_by
        self.resolved_at = timezone.now()
        self.status = self.STATUS_RESOLVED
        self.save(update_fields=["resolved", "resolved_to", "resolved_by", "resolved_at", "status"])

        if self.batch.failed_items > 0:
            self.batch.failed_items -= 1
        self.batch.matched_items += 1
        self.batch.save(update_fields=["matched_items", "failed_items"])

        return payslip

    def _load_unmatched_content(self):
        """Return unmatched file bytes handling legacy/suspicious paths gracefully."""

        storage = self.file.storage
        original_name = self.file.name
        candidates = [name for name in [original_name] if name]

        safe_basename = Path(original_name or "").name
        upload_prefix = (self.file.field.upload_to or "").rstrip("/\\")
        if safe_basename and upload_prefix:
            candidates.append(str(Path(upload_prefix) / safe_basename))

        last_error = None
        for name in candidates:
            try:
                with storage.open(name, "rb") as fh:
                    data = fh.read()
                if name != original_name and data:
                    # Normalize the stored name to a safe basename for future resolves.
                    self.file.save(safe_basename, ContentFile(data), save=True)
                return data
            except (FileNotFoundError, OSError, ValueError, SuspiciousFileOperation) as exc:
                last_error = exc

        raise FileNotFoundError(str(last_error) or "File non disponibile")
