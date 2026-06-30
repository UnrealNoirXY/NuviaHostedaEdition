from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

class Ticket(models.Model):
    STATUS_CHOICES = [
        ('open', 'Aperto'),
        ('in_progress', 'In lavorazione'),
        ('resolved', 'Risolto'),
        ('closed', 'Chiuso'),
    ]

    title = models.CharField(max_length=255)
    description = models.TextField()
    attachment = models.FileField(upload_to='ticket_attachments/', blank=True, null=True)
    room = models.ForeignKey('resort.Room', on_delete=models.SET_NULL, null=True, blank=True, related_name='tickets')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    due_date = models.DateTimeField(null=True, blank=True, verbose_name="Data di Scadenza")
    initial_due_date = models.DateTimeField(
        null=True,
        blank=True,
        editable=False,
        verbose_name="Scadenza iniziale",
        help_text="Scadenza comunicata da chi ha aperto il ticket.",
    )
    acknowledged_due_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Scadenza confermata",
        help_text="Scadenza confermata dal manutentore incaricato.",
    )
    acknowledged_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='acknowledged_tickets',
        verbose_name="Scadenza confermata da",
    )
    acknowledged_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Data conferma scadenza",
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open', db_index=True)
    completion_photo = models.ImageField(
        upload_to='ticket_completion_photos/',
        blank=True,
        null=True,
        help_text="Foto del lavoro completato obbligatoria per la chiusura."
    )
    deadline_reminder_sent_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp dell'ultimo promemoria inviato per la scadenza."
    )

    PRIORITY_LOW = 'low'
    PRIORITY_MEDIUM = 'medium'
    PRIORITY_HIGH = 'high'
    PRIORITY_URGENT = 'urgent'
    PRIORITY_CHOICES = [
        (PRIORITY_LOW, 'Bassa'),
        (PRIORITY_MEDIUM, 'Media'),
        (PRIORITY_HIGH, 'Alta'),
        (PRIORITY_URGENT, 'Urgente'),
    ]
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default=PRIORITY_MEDIUM, db_index=True)

    required_skill = models.ForeignKey('skills.Skill', on_delete=models.SET_NULL, null=True, blank=True, related_name='tickets', verbose_name="Competenza Richiesta")

    resort = models.ForeignKey('resort.Resort', on_delete=models.CASCADE, related_name='tickets')
    created_by = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='created_tickets')
    assigned_to = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_tickets')
    claimed_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='claimed_tickets',
        verbose_name="Presa in carico da",
    )
    claimed_at = models.DateTimeField(null=True, blank=True, verbose_name="Data presa in carico")
    first_claimed_at = models.DateTimeField(
        null=True,
        blank=True,
        editable=False,
        help_text="Prima volta in cui un manutentore ha preso in carico il ticket.",
    )
    last_released_at = models.DateTimeField(
        null=True,
        blank=True,
        editable=False,
        help_text="Ultima volta in cui il ticket è tornato non assegnato.",
    )
    unassigned_notification_sent_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp dell'ultimo broadcast per ticket non assegnato.",
    )
    notes = models.TextField(blank=True, null=True)
    estimated_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0'))],
        help_text="Costo stimato per completare il ticket."
    )
    actual_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0'))],
        help_text="Costo effettivo sostenuto per risolvere il ticket."
    )

    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"

class TicketComment(models.Model):
    ticket = models.ForeignKey('tickets.Ticket', on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey('accounts.User', on_delete=models.CASCADE)
    comment = models.TextField(blank=True)
    attachment = models.FileField(upload_to='comment_attachments/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Comment by {self.author.username} on {self.ticket.title}"

class TicketHistory(models.Model):
    ticket = models.ForeignKey('tickets.Ticket', on_delete=models.CASCADE, related_name='history')
    author = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=255)  # es. "Stato cambiato in...", "Nota aggiunta", ecc.
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']


class TicketDeadlineChange(models.Model):
    """Tiene traccia delle modifiche e proroghe della scadenza di un ticket."""

    CHANGE_SET = 'set'
    CHANGE_EXTEND = 'extend'
    CHANGE_SHORTEN = 'shorten'
    CHANGE_CHOICES = [
        (CHANGE_SET, 'Impostazione iniziale'),
        (CHANGE_EXTEND, 'Proroga'),
        (CHANGE_SHORTEN, 'Anticipo'),
    ]

    ticket = models.ForeignKey('tickets.Ticket', on_delete=models.CASCADE, related_name='deadline_changes')
    previous_due_date = models.DateTimeField(null=True, blank=True)
    new_due_date = models.DateTimeField(null=True, blank=True)
    changed_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, related_name='deadline_changes')
    justification = models.TextField(blank=True)
    change_type = models.CharField(max_length=16, choices=CHANGE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

class ProactiveMaintenanceAlert(models.Model):
    room = models.ForeignKey('resort.Room', on_delete=models.SET_NULL, null=True, related_name='proactive_alerts')
    reason = models.TextField(help_text="Motivo dell'allerta, es. '3 ticket in 30 giorni'.")
    last_ticket = models.ForeignKey('tickets.Ticket', on_delete=models.SET_NULL, null=True, help_text="L'ultimo ticket che ha generato l'allerta.")
    created_at = models.DateTimeField(auto_now_add=True)
    is_addressed = models.BooleanField(default=False, db_index=True, verbose_name="Gestita")

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Allerta Manutenzione Proattiva"
        verbose_name_plural = "Allerte Manutenzione Proattiva"

    def __str__(self):
        return f"Allerta per {self.room} - {self.created_at.strftime('%d/%m/%Y')}"
