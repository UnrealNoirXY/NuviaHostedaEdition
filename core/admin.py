from django.contrib import admin
from django.http import HttpResponseRedirect
from django.urls import reverse
from .models import (
    PlatformSettings,
    InAppGuideAsset,
    NuviaMailAccount,
    NuviaMailSignature,
    NuviaMailOnboardingEvent,
    NuviaMailTemplate,
    NuviaMailSendQueue,
    NuviaMailCompliancePolicy,
    NuviaMailFolder,
    NuviaMailThread,
    NuviaMailMessage,
    NuviaMailSyncCheckpoint,
)

@admin.register(PlatformSettings)
class PlatformSettingsAdmin(admin.ModelAdmin):
    """
    Admin View for PlatformSettings.
    Redirects the changelist view to the change form of the single settings object.
    """
    def changelist_view(self, request, extra_context=None):
        """
        Redirect to the change view of the single PlatformSettings object.
        """
        # Get the singleton object, creating it if it doesn't exist.
        settings_obj = PlatformSettings.load()
        return HttpResponseRedirect(
            reverse('admin:core_platformsettings_change', args=(settings_obj.pk,))
        )

    def has_add_permission(self, request):
        """
        Prevent adding new settings if one already exists.
        """
        return not PlatformSettings.objects.exists()


@admin.register(InAppGuideAsset)
class InAppGuideAssetAdmin(admin.ModelAdmin):
    list_display = ('title', 'guide_key', 'step_key', 'resource_type', 'position', 'is_active', 'updated_at')
    list_filter = ('guide_key', 'resource_type', 'is_active')
    search_fields = ('title', 'guide_key', 'step_key')
    ordering = ('guide_key', 'position', 'created_at')


@admin.register(NuviaMailAccount)
class NuviaMailAccountAdmin(admin.ModelAdmin):
    list_display = ('email_address', 'user', 'provider', 'auth_mode', 'is_active', 'oauth_connected_at', 'last_test_status', 'last_test_at', 'updated_at')
    list_filter = ('provider', 'auth_mode', 'is_active', 'last_test_status')
    search_fields = ('email_address', 'username', 'user__username', 'user__email')


@admin.register(NuviaMailSignature)
class NuviaMailSignatureAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'is_default', 'updated_at')
    list_filter = ('is_default',)
    search_fields = ('name', 'user__username', 'user__email')


@admin.register(NuviaMailOnboardingEvent)
class NuviaMailOnboardingEventAdmin(admin.ModelAdmin):
    list_display = ('user', 'event_type', 'created_at')
    list_filter = ('event_type', 'created_at')
    search_fields = ('user__username', 'user__email')


@admin.register(NuviaMailTemplate)
class NuviaMailTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'is_active', 'updated_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'subject', 'user__username', 'user__email')


@admin.register(NuviaMailSendQueue)
class NuviaMailSendQueueAdmin(admin.ModelAdmin):
    list_display = ('to_email', 'user', 'status', 'retry_count', 'compliance_flagged', 'scheduled_for', 'created_at')
    list_filter = ('status', 'compliance_flagged', 'scheduled_for', 'retry_count')
    search_fields = ('to_email', 'subject', 'user__username', 'user__email')


@admin.register(NuviaMailCompliancePolicy)
class NuviaMailCompliancePolicyAdmin(admin.ModelAdmin):
    list_display = ('user', 'enforce_external_domain_block', 'updated_at')
    list_filter = ('enforce_external_domain_block',)
    search_fields = ('user__username', 'user__email', 'allowed_domains')


@admin.register(NuviaMailFolder)
class NuviaMailFolderAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'account', 'is_inbox', 'is_sent', 'updated_at')
    list_filter = ('is_inbox', 'is_sent')
    search_fields = ('name', 'provider_folder_id', 'user__username')


@admin.register(NuviaMailThread)
class NuviaMailThreadAdmin(admin.ModelAdmin):
    list_display = ('subject', 'user', 'folder', 'last_message_at', 'updated_at')
    list_filter = ('folder',)
    search_fields = ('subject', 'provider_thread_id', 'user__username')


@admin.register(NuviaMailMessage)
class NuviaMailMessageAdmin(admin.ModelAdmin):
    list_display = ('subject', 'user', 'folder', 'thread', 'from_email', 'received_at')
    list_filter = ('folder', 'received_at')
    search_fields = ('subject', 'provider_message_id', 'from_email', 'to_emails')


@admin.register(NuviaMailSyncCheckpoint)
class NuviaMailSyncCheckpointAdmin(admin.ModelAdmin):
    list_display = ('user', 'account', 'folder', 'cursor', 'last_synced_at', 'updated_at')
    list_filter = ('last_synced_at',)
    search_fields = ('user__username', 'folder__name', 'cursor')
