from django.db import models
from django.conf import settings

class Announcement(models.Model):
    PRIORITY_NORMAL = 'normal'
    PRIORITY_HIGH = 'high'
    PRIORITY_URGENT = 'urgent'

    PRIORITY_CHOICES = [
        (PRIORITY_NORMAL, 'Normale'),
        (PRIORITY_HIGH, 'Alta'),
        (PRIORITY_URGENT, 'Urgente'),
    ]

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='authored_announcements'
    )
    title = models.CharField(max_length=255)
    body = models.TextField()
    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default=PRIORITY_NORMAL
    )
    recipients = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='announcements',
        blank=True
    )
    read_by = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='read_announcements',
        blank=True,
        verbose_name="Letto da"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['-created_at']

class RecipientGroup(models.Model):
    name = models.CharField(max_length=100, help_text="Dai un nome a questo gruppo, es. 'Tutti i Manutentori'")
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='recipient_groups'
    )
    users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='recipient_groups_member',
        blank=True
    )
    resorts = models.ManyToManyField(
        'resort.Resort',
        related_name='recipient_groups',
        blank=True
    )
    roles = models.CharField(max_length=255, blank=True, help_text="Elenco di ruoli separati da virgola")

    def __str__(self):
        return f"{self.name} (creato da {self.owner.username})"


from django_celery_beat.models import PeriodicTask
from django.utils import timezone

class ScheduledEmailReport(models.Model):
    FREQUENCY_DAILY = 'daily'
    FREQUENCY_WEEKLY = 'weekly'
    FREQUENCY_CHOICES = [
        (FREQUENCY_DAILY, 'Ogni Giorno'),
        (FREQUENCY_WEEKLY, 'Ogni Settimana'),
    ]

    DAY_OF_WEEK_CHOICES = [
        ('1', 'Lunedì'), ('2', 'Martedì'), ('3', 'Mercoledì'),
        ('4', 'Giovedì'), ('5', 'Venerdì'), ('6', 'Sabato'), ('0', 'Domenica'),
    ]

    name = models.CharField(max_length=200, help_text="Un nome per questo report programmato, es. 'Report Giornaliero Direttori'")
    recipients = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='email_reports', verbose_name="Destinatari")
    resorts = models.ManyToManyField('resort.Resort', help_text="Seleziona i resort da includere nel report.", verbose_name="Resort Inclusi")

    # Campi per la nuova logica di programmazione
    frequency = models.CharField(
        max_length=10,
        choices=FREQUENCY_CHOICES,
        default=FREQUENCY_DAILY,
        verbose_name="Frequenza di Invio"
    )
    day_of_week = models.CharField(
        max_length=1,
        choices=DAY_OF_WEEK_CHOICES,
        default='1',
        verbose_name="Giorno della Settimana (se settimanale)",
        blank=True
    )
    hour = models.IntegerField(default=8, verbose_name="Ora di invio")
    minute = models.IntegerField(default=0, verbose_name="Minuto di invio")

    review_period_days = models.PositiveIntegerField(
        default=1,
        verbose_name="Periodo Recensioni (giorni)",
        help_text="Includi le recensioni degli ultimi X giorni."
    )

    # Vecchi campi, mantenuti per la migrazione, ma non più usati nel form
    report_period = models.CharField(max_length=20, default='daily', editable=False)
    custom_start_date = models.DateField(null=True, blank=True, editable=False)
    custom_end_date = models.DateField(null=True, blank=True, editable=False)

    periodic_task = models.OneToOneField(PeriodicTask, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Task Programmato")
    is_active = models.BooleanField(default=True, help_text="Disattiva per sospendere l'invio programmato di questo report.", verbose_name="Attivo")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Report Email Programmato"
        verbose_name_plural = "Report Email Programmati"
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def get_resort_names(self):
        return ", ".join([r.name for r in self.resorts.all()])

    def get_recipient_names(self):
        return ", ".join([u.username for u in self.recipients.all()])


class EmailLog(models.Model):
    class Status(models.TextChoices):
        SUCCESS = "success", "Successo"
        FAILED = "failed", "Fallito"

    task_name = models.CharField(max_length=255)
    recipient = models.EmailField(blank=True)
    booking = models.ForeignKey("bookings.Booking", null=True, blank=True, on_delete=models.SET_NULL, related_name="email_logs")
    status = models.CharField(max_length=20, choices=Status.choices, db_index=True)
    error_message = models.TextField(blank=True)
    link_used = models.URLField(blank=True, null=True)
    celery_task_id = models.CharField(max_length=255, blank=True)
    payload = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.task_name} -> {self.recipient} ({self.status})"
