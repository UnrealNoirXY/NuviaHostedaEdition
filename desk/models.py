from django.db import models
from django.conf import settings

class WidgetPreference(models.Model):
    """
    Stores the personalized widget layout for a user.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='widget_preference'
    )
    layout = models.JSONField(
        default=dict,
        blank=True,
        help_text="A dictionary of layouts for different breakpoints, e.g., {'lg': [...], 'md': [...]}"
    )
    open_windows = models.JSONField(
        default=list,
        blank=True,
        help_text="A list of window IDs currently open on the desktop"
    )
    pinned_icons = models.JSONField(
        default=list,
        blank=True,
        help_text="A list of app IDs pinned to the desktop icons"
    )
    workspaces = models.JSONField(
        default=list,
        blank=True,
        help_text="Definition of virtual desktops/workspaces"
    )
    active_workspace_id = models.IntegerField(default=0)

    def __str__(self):
        return f"Layout for {self.user.username}"

class EventInvitation(models.Model):
    """
    Represents the status of an invitation for a specific user to a specific event.
    """
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('declined', 'Declined'),
    )

    event = models.ForeignKey('Event', on_delete=models.CASCADE, related_name="invitations")
    invitee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="event_invitations")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')

    class Meta:
        unique_together = ('event', 'invitee')
        verbose_name = "Invito Evento"
        verbose_name_plural = "Inviti Evento"

    def __str__(self):
        return f"{self.invitee.username}'s invitation to {self.event.title} is {self.status}"


class Event(models.Model):
    """
    Represents a calendar event.
    """
    EVENT_TYPE_CHOICES = (
        ('event', 'Evento'),
        ('task', 'Task'),
        ('appointment', 'Appuntamento'),
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_events',
        help_text="The user who created the event."
    )
    title = models.CharField(max_length=200)
    start = models.DateTimeField()
    end = models.DateTimeField()
    event_type = models.CharField(max_length=20, choices=EVENT_TYPE_CHOICES, default='event')
    attendees = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through='EventInvitation',
        related_name='attended_events',
        help_text="Users who are invited to this event."
    )


    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "Evento"
        verbose_name_plural = "Eventi"
