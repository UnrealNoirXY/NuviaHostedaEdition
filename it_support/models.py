from django.db import models
from django.conf import settings

class IT_Ticket(models.Model):
    STATUS_CHOICES = (
        ('open', 'Aperto'),
        ('in_progress', 'In Lavorazione'),
        ('resolved', 'Risolto'),
        ('closed', 'Chiuso'),
    )
    PRIORITY_CHOICES = (
        ('low', 'Bassa'),
        ('medium', 'Media'),
        ('high', 'Alta'),
        ('urgent', 'Urgente'),
    )
    DEVICE_CHOICES = (
        ('pc', 'PC/Laptop'),
        ('printer', 'Stampante'),
        ('network', 'Rete/Wi-Fi'),
        ('software', 'Software/Applicativo'),
        ('other', 'Altro'),
    )

    title = models.CharField(max_length=255, help_text="Titolo breve e descrittivo del problema IT.")
    description = models.TextField(help_text="Descrizione dettagliata del problema.")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='it_tickets')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open', db_index=True)
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium', db_index=True)
    device_type = models.CharField(max_length=20, choices=DEVICE_CHOICES, default='other', verbose_name="Tipo di Dispositivo")
    anydesk_id = models.CharField(max_length=50, blank=True, verbose_name="ID AnyDesk", help_text="Se pertinente, inserire l'ID AnyDesk per l'assistenza remota.")
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_it_tickets')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    attachment = models.FileField(upload_to='it_ticket_attachments/', blank=True, null=True, help_text="Allega screenshot o file di log.")
    asset = models.ForeignKey('assets.Asset', on_delete=models.SET_NULL, null=True, blank=True, related_name='it_tickets', verbose_name="Asset Correlato")
    intervention_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Costo Intervento")

    CHAT_STATUS_CHOICES = (
        ('none', 'Nessuna Richiesta'),
        ('requested', 'Richiesta in Attesa'),
        ('active', 'Attiva'),
        ('declined', 'Rifiutata'),
        ('ended', 'Terminata'),
    )
    chat_status = models.CharField(max_length=20, choices=CHAT_STATUS_CHOICES, default='none')

    def __str__(self):
        return f"IT Support Ticket: {self.title} ({self.get_status_display()})"

    class Meta:
        verbose_name = "Ticket IT"
        verbose_name_plural = "Tickets IT"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['priority']),
            models.Index(fields=['user']),
        ]

class ChatMessage(models.Model):
    ticket = models.ForeignKey(IT_Ticket, on_delete=models.CASCADE, related_name='chat_messages')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='it_chat_messages')
    message = models.TextField(blank=True)
    attachment = models.FileField(upload_to='it_chat_attachments/', blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp']
        verbose_name = "Messaggio Chat IT"
        verbose_name_plural = "Messaggi Chat IT"

    def __str__(self):
        return f"Message by {self.author.username} on ticket #{self.ticket.pk}"

class IT_TicketComment(models.Model):
    ticket = models.ForeignKey(IT_Ticket, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='it_ticket_comments')
    comment = models.TextField()
    attachment = models.FileField(upload_to='it_comment_attachments/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Comment by {self.author.username} on IT Ticket #{self.ticket.pk}"
