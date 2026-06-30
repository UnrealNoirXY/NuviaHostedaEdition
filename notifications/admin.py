from django.contrib import admin

from .models import Notification, PushSubscription


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        'display_title',
        'user',
        'category',
        'priority',
        'is_read',
        'is_pinned',
        'created_at',
    )
    list_filter = ('category', 'priority', 'is_read', 'is_pinned', 'requires_acknowledgement')
    search_fields = ('message', 'title', 'user__username')
    autocomplete_fields = ('user', 'audience_company', 'audience_resort')
    ordering = ('-created_at',)


@admin.register(PushSubscription)
class PushSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('endpoint', 'user', 'device_type', 'is_active', 'created_at')
    list_filter = ('device_type', 'is_active')
    search_fields = ('endpoint', 'user__username', 'user_agent')
    autocomplete_fields = ('user',)
