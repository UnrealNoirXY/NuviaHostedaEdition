import re
from pathlib import Path

from rest_framework import serializers
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError as DjangoValidationError

from .models import (
    HREventLog,
    HRDocument,
    HRNotification,
    HRNotificationDelivery,
    ListeningTicket,
    ListeningTicketMessage,
    NotificationPreference,
    Payslip,
    PayslipBatch,
    PayslipUnmatched,
)


class HRDocumentSerializer(serializers.ModelSerializer):
    file = serializers.SerializerMethodField()
    file_name = serializers.SerializerMethodField()
    is_acknowledged = serializers.SerializerMethodField()

    class Meta:
        model = HRDocument
        fields = [
            "id",
            "title",
            "description",
            "category",
            "file",
            "file_name",
            "audience_roles",
            "audience_company",
            "audience_resort",
            "requires_acknowledgement",
            "is_acknowledged",
            "visible_from",
            "visible_until",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def validate(self, attrs):
        user = self.context["request"].user
        hr_role = getattr(getattr(user, "__class__", None), "RISORSE_UMANE", None)
        if not user.is_superuser and getattr(user, "role", None) != hr_role:
            raise serializers.ValidationError("Solo HR o superadmin possono pubblicare documenti.")
        return attrs

    def create(self, validated_data):
        validated_data["uploaded_by"] = self.context["request"].user
        return super().create(validated_data)

    def get_file(self, obj):
        file_field = getattr(obj, "file", None)
        try:
            if file_field:
                return file_field.url
        except ValueError:
            return None
        return None

    def get_file_name(self, obj):
        file_field = getattr(obj, "file", None)
        name = getattr(file_field, "name", None)
        return Path(name).name if name else None

    def get_is_acknowledged(self, obj):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False
        return obj.acknowledged_by.filter(pk=user.pk).exists()


class PayslipSerializer(serializers.ModelSerializer):
    file = serializers.SerializerMethodField()
    file_name = serializers.SerializerMethodField()
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = Payslip
        fields = [
            "id",
            "user",
            "batch",
            "company",
            "resort",
            "period_label",
            "file",
            "file_name",
            "download_url",
            "status",
            "auto_matched",
            "metadata",
            "downloaded_at",
            "created_at",
        ]
        read_only_fields = ["auto_matched", "metadata", "created_at", "downloaded_at", "status"]

    def get_file(self, obj):
        file_field = getattr(obj, "file", None)
        try:
            if file_field:
                return file_field.url
        except ValueError:
            return None
        return None

    def get_file_name(self, obj):
        file_field = getattr(obj, "file", None)
        name = getattr(file_field, "name", None)
        return Path(name).name if name else None

    def get_download_url(self, obj):
        request = self.context.get("request")
        if not request:
            return None
        return request.build_absolute_uri(reverse("hr_portal:download_payslip", args=[obj.pk]))


class HRNotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = HRNotification
        fields = [
            "id",
            "title",
            "body",
            "category",
            "status",
            "scheduled_for",
            "expires_at",
            "cta_label",
            "cta_url",
            "cta_type",
            "audience_roles",
            "audience_company",
            "audience_resort",
            "delivered_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["delivered_count", "created_at", "updated_at"]

    def validate(self, attrs):
        user = self.context["request"].user
        hr_role = getattr(getattr(user, "__class__", None), "RISORSE_UMANE", None)
        if not user.is_superuser and getattr(user, "role", None) != hr_role:
            raise serializers.ValidationError("Solo HR o superadmin possono gestire le notifiche.")
        cta_label = (attrs.get("cta_label") or "").strip()
        cta_url = (attrs.get("cta_url") or "").strip()
        if cta_label and not cta_url:
            raise serializers.ValidationError({"cta_url": "Inserisci anche l'URL della CTA."})
        if cta_url and not cta_label:
            raise serializers.ValidationError({"cta_label": "Inserisci anche la label della CTA."})
        if cta_url:
            if cta_url.startswith("/"):
                return attrs
            validator = URLValidator(schemes=["http", "https"])
            try:
                validator(cta_url)
            except DjangoValidationError:
                raise serializers.ValidationError({"cta_url": "Inserisci un URL valido (https://...) o relativo (/privacy-policy/)."})
        return attrs

    def create(self, validated_data):
        validated_data["created_by"] = self.context["request"].user
        return super().create(validated_data)


class HRNotificationDeliverySerializer(serializers.ModelSerializer):
    class Meta:
        model = HRNotificationDelivery
        fields = [
            "id",
            "notification",
            "user",
            "channel",
            "status",
            "sent_at",
            "error",
            "created_at",
        ]
        read_only_fields = ["created_at", "notification", "user"]


class PayslipBatchSerializer(serializers.ModelSerializer):
    processing_log = serializers.JSONField(read_only=True)
    matched_items = serializers.IntegerField(read_only=True)
    failed_items = serializers.IntegerField(read_only=True)
    total_items = serializers.IntegerField(read_only=True)
    auto_match_rate = serializers.FloatField(read_only=True)
    processing_duration_ms = serializers.IntegerField(read_only=True)
    manual_assignments = serializers.JSONField(required=False)
    quality_kpis = serializers.SerializerMethodField()

    class Meta:
        model = PayslipBatch
        fields = [
            "id",
            "source_file",
            "uploaded_by",
            "company",
            "resort",
            "status",
            "auto_match_strategy",
            "manifest_hint",
            "enable_ocr",
            "ocr_languages",
            "manual_assignments",
            "total_items",
            "matched_items",
            "failed_items",
            "auto_match_rate",
            "quality_kpis",
            "processing_duration_ms",
            "processed_at",
            "processing_log",
            "created_at",
        ]
        read_only_fields = [
            "uploaded_by",
            "status",
            "processed_at",
            "created_at",
            "processing_log",
            "matched_items",
            "failed_items",
            "total_items",
            "auto_match_rate",
            "quality_kpis",
            "processing_duration_ms",
        ]

    def get_quality_kpis(self, obj):
        processing_log = obj.processing_log or []
        total_items = obj.total_items or 0
        error_count = sum(1 for entry in processing_log if entry.get("status") == "error")
        ocr_error_count = sum(
            1 for entry in processing_log if entry.get("status") in {"ocr_error", "ocr_unavailable"}
        )
        error_rate = round((error_count / total_items) * 100, 1) if total_items else 0
        ocr_success_rate = None
        if obj.enable_ocr:
            ocr_success_rate = round(100 - ((ocr_error_count / total_items) * 100), 1) if total_items else 0
        return {
            "error_count": error_count,
            "error_rate": error_rate,
            "ocr_error_count": ocr_error_count,
            "ocr_success_rate": ocr_success_rate,
        }

    def create(self, validated_data):
        user = self.context["request"].user
        validated_data["uploaded_by"] = user
        batch = super().create(validated_data)
        HREventLog.record(
            event_type="payslip_batch_created",
            actor=user,
            target=batch,
            metadata={
                "batch_id": str(batch.pk),
                "preview_token": str(self.initial_data.get("preview_token") or "").strip(),
                "has_preview_token": bool(self.initial_data.get("preview_token")),
            },
        )
        batch.process(actor=user)
        return batch

    def validate_manifest_hint(self, value):
        if value:
            try:
                re.compile(value)
            except re.error as exc:
                raise serializers.ValidationError(f"Regex non valida: {exc}")
        return value

    def validate_manual_assignments(self, value):
        if value in (None, ""):
            return {}
        if not isinstance(value, dict):
            raise serializers.ValidationError("Manual assignments deve essere un oggetto JSON.")
        segments = value.get("segments", {})
        if segments and not isinstance(segments, dict):
            raise serializers.ValidationError("Manual assignments.segments deve essere un oggetto JSON.")
        normalized = {}
        for segment_key, user_id in (segments or {}).items():
            if user_id in (None, ""):
                continue
            if isinstance(user_id, dict):
                normalized_value = {}
                if user_id.get("user_id") or user_id.get("user"):
                    normalized_value["user_id"] = str(user_id.get("user_id") or user_id.get("user"))
                if user_id.get("period_label"):
                    period_label = str(user_id.get("period_label"))
                    if not re.fullmatch(r"20\d{2}-(0[1-9]|1[0-2])", period_label):
                        raise serializers.ValidationError("Manual assignments.period_label deve essere nel formato YYYY-MM.")
                    normalized_value["period_label"] = period_label
                if normalized_value:
                    normalized[str(segment_key)] = normalized_value
            else:
                normalized[str(segment_key)] = str(user_id)
        value["segments"] = normalized
        return value


class PayslipUnmatchedSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    file_name = serializers.SerializerMethodField()

    class Meta:
        model = PayslipUnmatched
        fields = [
            "id",
            "batch",
            "identifier",
            "file",
            "file_name",
            "company",
            "resort",
            "resolved",
            "status",
            "status_display",
            "resolved_to",
            "resolved_by",
            "resolved_at",
            "created_at",
        ]
        read_only_fields = [
            "batch",
            "file",
            "file_name",
            "company",
            "resort",
            "resolved",
            "status",
            "status_display",
            "resolved_to",
            "resolved_by",
            "resolved_at",
            "created_at",
        ]

    def get_file_name(self, obj):
        file_field = getattr(obj, "file", None)
        name = getattr(file_field, "name", None)
        return Path(name).name if name else None


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        fields = [
            "id",
            "user",
            "allow_email",
            "allow_push",
            "allow_sms",
            "quiet_hours_start",
            "quiet_hours_end",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["user", "created_at", "updated_at"]

    def validate(self, attrs):
        start = attrs.get("quiet_hours_start", getattr(self.instance, "quiet_hours_start", None))
        end = attrs.get("quiet_hours_end", getattr(self.instance, "quiet_hours_end", None))
        if bool(start) ^ bool(end):
            raise serializers.ValidationError("Imposta sia inizio sia fine delle quiet hours.")
        if start and end and start == end:
            raise serializers.ValidationError("L'intervallo di quiet hours non può essere vuoto.")
        return attrs


class ListeningTicketMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ListeningTicketMessage
        fields = ["id", "ticket", "author", "body", "is_internal", "created_at"]
        read_only_fields = ["ticket", "author", "created_at"]


class ListeningTicketSerializer(serializers.ModelSerializer):
    messages = ListeningTicketMessageSerializer(many=True, read_only=True)

    class Meta:
        model = ListeningTicket
        fields = [
            "id",
            "author",
            "assigned_to",
            "company",
            "resort",
            "subject",
            "message",
            "is_anonymous",
            "priority",
            "status",
            "sentiment",
            "sla_hours",
            "due_at",
            "closed_at",
            "tags",
            "created_at",
            "updated_at",
            "messages",
        ]
        read_only_fields = [
            "author",
            "created_at",
            "updated_at",
            "sentiment",
            "due_at",
            "closed_at",
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if instance.is_anonymous and not (
            getattr(user, "is_superuser", False)
            or getattr(user, "role", None)
            == getattr(getattr(user, "__class__", None), "RISORSE_UMANE", None)
        ):
            data["author"] = None
        return data


class HREventLogSerializer(serializers.ModelSerializer):
    event_type_display = serializers.CharField(source="get_event_type_display", read_only=True)

    class Meta:
        model = HREventLog
        fields = [
            "id",
            "event_type",
            "event_type_display",
            "actor",
            "target_model",
            "target_id",
            "metadata",
            "company",
            "resort",
            "created_at",
        ]
        read_only_fields = fields
from django.urls import reverse
