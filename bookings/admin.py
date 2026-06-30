from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from .models import Booking, CheckInProcess, Guest, GuestDocument, Consent, NewsletterSubscription, AuditLog
from .tasks import (
    send_invitation_email_task,
    send_booking_creation_email_task,
    send_booking_update_email_task,
    send_booking_deletion_email_task
)
from .utils import get_booking_details_for_email
from communications.email_gateway import dispatch_email_task


class GuestInline(admin.TabularInline):
    model = Guest
    extra = 0
    readonly_fields = ('first_name', 'last_name', 'date_of_birth')
    can_delete = False
    def has_add_permission(self, request, obj=None): return False

class CheckInProcessInline(admin.StackedInline):
    model = CheckInProcess
    readonly_fields = ('state', 'completed_at', 'signed_pdf_url', 'signature_meta')
    can_delete = False
    def has_add_permission(self, request, obj=None): return False

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('guest_name', 'display_booking_id', 'check_in_date', 'resort', 'status', 'completed_at_display')
    list_filter = ('status', 'resort', 'check_in_date')
    search_fields = ('guest_name', 'guest_email', 'booking_engine_id')
    inlines = [GuestInline, CheckInProcessInline]
    actions = ['send_checkin_invitation', 'lock_access', 'unlock_access']

    def get_fieldsets(self, request, obj=None):
        """Mostra fieldset diversi per la creazione e la modifica."""
        creation_fieldsets = (
            ('Informazioni Principali', {'fields': ('guest_name', 'guest_email', 'status', 'resort')}),
            ('Date Soggiorno', {'fields': ('check_in_date', 'check_out_date')}),
            ('Dettagli Aggiuntivi', {'fields': ('room_details',)}),
            ('Identificativo Esterno (Opzionale)', {'fields': ('booking_engine_id',)}),
        )
        if obj:  # Vista di modifica
            change_fieldsets = (
                ('Informazioni Principali', {'fields': ('guest_name', 'guest_email', 'status', 'resort')}),
                ('Date Soggiorno', {'fields': ('check_in_date', 'check_out_date')}),
                ('Dettagli Aggiuntivi', {'fields': ('room_details',)}),
                ('Dati Interni', {'fields': ('booking_engine_id', 'created_at', 'updated_at'), 'classes': ('collapse',)}),
            )
            return change_fieldsets
        return creation_fieldsets

    def get_readonly_fields(self, request, obj=None):
        """Rende i campi non modificabili solo nella vista di modifica."""
        if obj:
            return ('booking_engine_id', 'created_at', 'updated_at')
        return ()

    @admin.display(description="ID Booking Engine")
    def display_booking_id(self, obj):
        return obj.booking_engine_id if obj.booking_engine_id else "Manuale"

    def log_action(self, request, queryset, action_type):
        for booking in queryset:
            AuditLog.objects.create(user=request.user, action=action_type, target_booking=booking, details={'source_ip': request.META.get('REMOTE_ADDR')})

    def save_model(self, request, obj, form, change):
        """Attiva le notifiche email alla creazione o modifica di una prenotazione."""
        is_new = not obj.pk
        super().save_model(request, obj, form, change)
        scheme = request.scheme
        host = request.get_host()
        if is_new:
            dispatch_email_task(send_booking_creation_email_task, obj.id, scheme, host)
        else:
            dispatch_email_task(send_booking_update_email_task, obj.id, scheme, host)

    def delete_model(self, request, obj):
        """Attiva la notifica email prima di cancellare un singolo oggetto."""
        booking_details = get_booking_details_for_email(obj, request)
        dispatch_email_task(send_booking_deletion_email_task, booking_details)
        super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        """Attiva le notifiche email prima di cancellare un queryset di oggetti."""
        for booking in queryset:
            booking_details = get_booking_details_for_email(booking, request)
            dispatch_email_task(send_booking_deletion_email_task, booking_details)
        super().delete_queryset(request, queryset)

    @admin.action(description="Invia Invito al Check-in (Asincrono)")
    def send_checkin_invitation(self, request, queryset):
        task_count = 0
        scheme = request.scheme
        host = request.get_host()
        for booking in queryset:
            dispatch_email_task(send_invitation_email_task, booking.id, scheme, host)
            task_count += 1

        if task_count > 0:
            self.message_user(request, f"Invio dell'invito al check-in programmato per {task_count} prenotazioni.")
        self.log_action(request, queryset, AuditLog.Action.REGENERATED_TOKEN)

    @admin.action(description="Blocca Accesso al Check-in")
    def lock_access(self, request, queryset):
        from django.utils import timezone
        queryset.update(locked_at=timezone.now())
        self.log_action(request, queryset, AuditLog.Action.LOCKED_ACCESS)
        self.message_user(request, f"Accesso bloccato per {queryset.count()} prenotazioni.")

    @admin.action(description="Sblocca Accesso al Check-in")
    def unlock_access(self, request, queryset):
        queryset.update(locked_at=None)
        self.log_action(request, queryset, AuditLog.Action.UNLOCKED_ACCESS)
        self.message_user(request, f"Accesso sbloccato per {queryset.count()} prenotazioni.")

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('checkin_process')

    def completed_at_display(self, obj):
        if hasattr(obj, 'checkin_process'): return obj.checkin_process.completed_at
        return None
    completed_at_display.short_description = 'Check-in Completato il'

@admin.register(Guest)
class GuestAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'booking_link')
    search_fields = ('first_name', 'last_name', 'booking__guest_name')

    def booking_link(self, obj):
        from django.urls import reverse
        from django.utils.html import format_html
        link = reverse("admin:bookings_booking_change", args=[obj.booking.id])
        return format_html('<a href="{}">{}</a>', link, obj.booking)
    booking_link.short_description = 'Prenotazione'

@admin.register(GuestDocument)
class GuestDocumentAdmin(admin.ModelAdmin):
    list_display = ('guest', 'secure_document_link', 'uploaded_at', 'scanned_at', 'scan_result', 'ocr_confidence')
    list_filter = ('scan_result', 'ocr_confidence',)
    search_fields = ('guest__first_name', 'guest__last_name',)
    readonly_fields = ('guest', 'secure_document_link', 'sha256_hash', 'uploaded_at', 'scanned_at', 'scan_result', 'ocr_confidence')

    def secure_document_link(self, obj):
        if obj.file:
            # Genera l'URL per la vista di download sicura
            url = reverse('bookings:serve_document', args=[obj.pk])
            return format_html('<a href="{}" target="_blank">Apri Documento</a>', url)
        return "N/A"
    secure_document_link.short_description = 'Download Sicuro'

    def get_readonly_fields(self, request, obj=None):
        # Rende il campo 'file' non modificabile dopo il primo upload
        if obj and obj.file:
            return self.readonly_fields + ('file',)
        return self.readonly_fields

@admin.register(NewsletterSubscription)
class NewsletterSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('email', 'subscribed_at')
    search_fields = ('email',)

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'user', 'action', 'target_booking')
    list_filter = ('action', 'user')
    search_fields = ('user__username', 'target_booking__guest_name')
    readonly_fields = [f.name for f in AuditLog._meta.fields]

    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False
    def has_delete_permission(self, request, obj=None): return False