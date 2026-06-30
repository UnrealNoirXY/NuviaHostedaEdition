from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import PrivacyPolicyVersion, User, UserPrivacyConsent
from .emails import send_privacy_confirmation_email

class CustomUserAdmin(UserAdmin):
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password', 'password2', 'fiscal_code'),
        }),
        ('Personal info', {'fields': ('first_name', 'last_name')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Custom Fields', {'fields': ('role', 'resort', 'company', 'can_export_review_reports', 'has_inventory_access', 'can_manage_purchase_orders', 'menu_creation_studio_enabled')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    fieldsets = UserAdmin.fieldsets + (
        (None, {'fields': ('role', 'resort', 'company', 'fiscal_code', 'can_export_review_reports', 'has_inventory_access', 'can_manage_purchase_orders', 'menu_creation_studio_enabled')}),
    )
    list_display = ('username', 'email', 'role', 'resort', 'is_staff', 'can_export_review_reports', 'menu_creation_studio_enabled')
    actions = ["resend_privacy_confirmation"]

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(super().get_readonly_fields(request, obj))
        if not request.user.is_superuser and getattr(request.user, "role", None) != User.OWNER:
            readonly_fields.append("fiscal_code")
        return readonly_fields

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if obj is None and "fiscal_code" in form.base_fields:
            form.base_fields["fiscal_code"].required = True
        return form

    @admin.action(description="Reinvia email conferma privacy")
    def resend_privacy_confirmation(self, request, queryset):
        sent_count = 0
        for user in queryset:
            try:
                if send_privacy_confirmation_email(user):
                    sent_count += 1
            except Exception:
                continue
        self.message_user(request, f"Email inviate: {sent_count}")

@admin.register(PrivacyPolicyVersion)
class PrivacyPolicyVersionAdmin(admin.ModelAdmin):
    list_display = ("version", "published_at", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("version", "content")


@admin.register(UserPrivacyConsent)
class UserPrivacyConsentAdmin(admin.ModelAdmin):
    list_display = ("user", "policy_version", "accepted_at", "payslip_email_opt_in", "email_confirmed_at")
    list_filter = ("payslip_email_opt_in", "policy_version")
    search_fields = ("user__username", "user__email", "policy_version__version")


admin.site.register(User, CustomUserAdmin)
