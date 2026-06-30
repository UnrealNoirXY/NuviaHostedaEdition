from django.contrib import admin
from .models import IT_Ticket

@admin.register(IT_Ticket)
class IT_TicketAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'status', 'priority', 'device_type', 'assigned_to', 'created_at')
    list_filter = ('status', 'priority', 'device_type', 'created_at')
    search_fields = ('title', 'description', 'user__username', 'assigned_to__username')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('title', 'description', 'user')
        }),
        ('Dettagli IT', {
            'fields': ('device_type', 'anydesk_id', 'attachment')
        }),
        ('Stato e Assegnazione', {
            'fields': ('status', 'priority', 'assigned_to')
        }),
        ('Date', {
            'fields': ('created_at', 'updated_at')
        }),
    )
