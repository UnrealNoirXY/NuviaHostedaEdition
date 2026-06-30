from django.contrib import admin

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


@admin.register(HRDocument)
class HRDocumentAdmin(admin.ModelAdmin):
    list_display = ["title", "category", "audience_company", "audience_resort", "requires_acknowledgement", "created_at"]
    list_filter = ["category", "requires_acknowledgement", "audience_company", "audience_resort"]
    search_fields = ["title", "description"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(HRNotification)
class HRNotificationAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "category",
        "status",
        "cta_label",
        "cta_type",
        "scheduled_for",
        "expires_at",
        "audience_company",
        "audience_resort",
    ]
    list_filter = ["status", "category", "audience_company", "audience_resort"]
    search_fields = ["title", "body"]
    readonly_fields = ["delivered_count", "created_at", "updated_at"]


@admin.register(HRNotificationDelivery)
class HRNotificationDeliveryAdmin(admin.ModelAdmin):
    list_display = ["notification", "user", "channel", "status", "sent_at", "error"]
    list_filter = ["channel", "status", "sent_at"]
    search_fields = ["notification__title", "user__username", "user__email", "error"]
    readonly_fields = ["notification", "user", "channel", "sent_at", "created_at"]


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ["user", "allow_email", "allow_push", "allow_sms", "quiet_hours_start", "quiet_hours_end"]
    search_fields = ["user__username", "user__email"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(PayslipBatch)
class PayslipBatchAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "status",
        "company",
        "resort",
        "enable_ocr",
        "auto_match_rate",
        "processing_duration_ms",
        "total_items",
        "matched_items",
        "failed_items",
        "created_at",
    ]
    list_filter = ["status", "company", "resort", "enable_ocr"]
    readonly_fields = [
        "processing_log",
        "processed_at",
        "processing_duration_ms",
        "auto_match_rate",
        "created_at",
    ]


@admin.register(Payslip)
class PayslipAdmin(admin.ModelAdmin):
    list_display = ["user", "company", "resort", "period_label", "status", "auto_matched", "created_at"]
    list_filter = ["status", "auto_matched", "company", "resort"]
    search_fields = ["user__username", "period_label"]


@admin.register(PayslipUnmatched)
class PayslipUnmatchedAdmin(admin.ModelAdmin):
    list_display = ["identifier", "batch", "company", "resort", "status", "created_at", "resolved_at"]
    list_filter = ["resolved", "status", "company", "resort"]
    readonly_fields = ["batch", "file", "created_at", "resolved_at", "resolved_by", "resolved_to"]


@admin.register(ListeningTicket)
class ListeningTicketAdmin(admin.ModelAdmin):
    list_display = ["subject", "company", "resort", "priority", "status", "due_at", "created_at"]
    list_filter = ["priority", "status", "company", "resort"]
    search_fields = ["subject", "message"]
    readonly_fields = ["created_at", "updated_at", "due_at", "closed_at"]


@admin.register(ListeningTicketMessage)
class ListeningTicketMessageAdmin(admin.ModelAdmin):
    list_display = ["ticket", "author", "is_internal", "created_at"]
    list_filter = ["is_internal"]
    search_fields = ["body", "ticket__subject"]
    readonly_fields = ["created_at"]


@admin.register(HREventLog)
class HREventLogAdmin(admin.ModelAdmin):
    list_display = ["event_type", "target_model", "target_id", "actor", "company", "resort", "created_at"]
    list_filter = ["event_type", "company", "resort", "created_at"]
    search_fields = ["target_id", "target_model", "metadata"]
    readonly_fields = ["created_at"]
