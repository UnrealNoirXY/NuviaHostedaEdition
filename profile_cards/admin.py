from django.contrib import admin

from .models import CardTemplate, ProfileCard, ProfileCardDelivery, ProfileCardEvent, ProfileCardPublicToken, ProfileCardSettings


@admin.register(CardTemplate)
class CardTemplateAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "company_name", "version", "is_default", "is_active")
    list_filter = ("is_default", "is_active")
    search_fields = ("name", "company_name")


@admin.register(ProfileCardSettings)
class ProfileCardSettingsAdmin(admin.ModelAdmin):
    list_display = ("singleton_key", "default_token_days", "require_phone", "require_department", "enable_multi_brand_templates")


@admin.register(ProfileCard)
class ProfileCardAdmin(admin.ModelAdmin):
    list_display = ("id", "first_name", "last_name", "role", "email", "status", "template", "applied_template_version", "updated_at")
    list_filter = ("status", "template")
    search_fields = ("first_name", "last_name", "email", "phone", "department")


@admin.register(ProfileCardPublicToken)
class ProfileCardPublicTokenAdmin(admin.ModelAdmin):
    list_display = ("id", "card", "token", "expires_at", "revoked_at", "open_count")
    search_fields = ("token", "card__first_name", "card__last_name", "card__email")


@admin.register(ProfileCardDelivery)
class ProfileCardDeliveryAdmin(admin.ModelAdmin):
    list_display = ("id", "card", "recipient_email", "status", "attempts", "sent_at")
    list_filter = ("status",)


@admin.register(ProfileCardEvent)
class ProfileCardEventAdmin(admin.ModelAdmin):
    list_display = ("id", "card", "event_type", "source", "created_at")
    list_filter = ("event_type",)
