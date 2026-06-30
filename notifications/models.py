import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone


class NotificationQuerySet(models.QuerySet):
    def _build_scope_filters(self, user):
        company_filter = models.Q(audience_company__isnull=True)
        if getattr(user, "company_id", None):
            company_filter |= models.Q(audience_company=user.company)

        resort_filter = models.Q(audience_resort__isnull=True)
        if getattr(user, "resort_id", None):
            resort_filter |= models.Q(audience_resort=user.resort)

        scope_filter = models.Q(user=user) | (
            models.Q(user__isnull=True) & company_filter & resort_filter
        )

        return scope_filter

    def targeted_to(self, user):
        """Return a queryset containing notifications that may be visible to the given user."""

        now = timezone.now()
        scope_filter = self._build_scope_filters(user)
        base_queryset = (
            self.filter(scope_filter)
            .filter(models.Q(expires_at__isnull=True) | models.Q(expires_at__gt=now))
            .select_related("user", "audience_company", "audience_resort")
        )

        matching_ids = [
            notification.pk
            for notification in base_queryset
            if notification.matches_user(user)
        ]

        if not matching_ids:
            return self.none()

        return self.filter(pk__in=matching_ids).select_related(
            "user", "audience_company", "audience_resort"
        )

    def unread_for(self, user):
        return self.targeted_to(user).filter(is_read=False)


class Notification(models.Model):
    class Category(models.TextChoices):
        GENERAL = "general", "Generale"
        TASK = "task", "Attività"
        ALERT = "alert", "Avviso"
        SYSTEM = "system", "Sistema"

    class Priority(models.TextChoices):
        LOW = "low", "Bassa"
        NORMAL = "normal", "Normale"
        HIGH = "high", "Alta"
        URGENT = "urgent", "Urgente"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
        null=True,
        blank=True,
        db_index=True,
    )
    message = models.CharField(max_length=255)
    title = models.CharField(max_length=150, blank=True, default="")
    body = models.TextField(blank=True, default="")
    link = models.URLField(blank=True, default="")
    cta_label = models.CharField(max_length=60, blank=True, default="Apri")
    category = models.CharField(
        max_length=20, choices=Category.choices, default=Category.GENERAL, db_index=True
    )
    priority = models.CharField(
        max_length=10, choices=Priority.choices, default=Priority.NORMAL, db_index=True
    )
    icon = models.CharField(max_length=50, blank=True, default="fa-bell")
    audience_roles = models.JSONField(blank=True, default=list, help_text="Lista di ruoli destinatari se la notifica è condivisa.")
    audience_company = models.ForeignKey(
        "clients.Company",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications",
    )
    audience_resort = models.ForeignKey(
        "resort.Resort",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications",
    )
    metadata = models.JSONField(blank=True, default=dict)
    is_read = models.BooleanField(default=False, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True)
    is_pinned = models.BooleanField(default=False, db_index=True)
    requires_acknowledgement = models.BooleanField(default=False)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    delivery_channels = models.JSONField(blank=True, default=list, help_text="Canali di consegna utilizzati (es. ['in_app', 'push']).")
    source = models.CharField(max_length=50, blank=True, default="")

    objects = NotificationQuerySet.as_manager()

    class Meta:
        ordering = ["-is_pinned", "-created_at"]
        indexes = [
            models.Index(fields=["category", "is_read"]),
            models.Index(fields=["priority", "is_read"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        recipient = self.user.username if self.user_id else "broadcast"
        return f"Notification for {recipient}: {self.display_title}"

    @property
    def display_title(self):
        return self.title or self.message

    def mark_as_read(self, timestamp=None, save=True):
        if not self.is_read:
            self.is_read = True
            self.read_at = timestamp or timezone.now()
            if save:
                self.save(update_fields=["is_read", "read_at", "updated_at"])

    def matches_user(self, user):
        if self.user_id and self.user_id != user.id:
            return False

        if self.audience_company_id and getattr(user, "company_id", None) != self.audience_company_id:
            return False

        if self.audience_resort_id and getattr(user, "resort_id", None) != self.audience_resort_id:
            return False

        if self.audience_roles:
            user_role = getattr(user, "role", None)
            if not user_role or user_role not in self.audience_roles:
                return False

        return True

    def to_payload(self):
        return {
            "id": self.pk,
            "title": self.display_title,
            "message": self.message,
            "body": self.body,
            "category": self.category,
            "priority": self.priority,
            "icon": self.icon or "fa-bell",
            "cta_label": self.cta_label or "Apri",
            "cta_url": self.link,
            "is_pinned": self.is_pinned,
            "metadata": self.metadata,
        }


class PushSubscription(models.Model):
    DEVICE_WEB = "web"
    DEVICE_ANDROID = "android"
    DEVICE_IOS = "ios"
    DEVICE_CHOICES = [
        (DEVICE_WEB, "Web"),
        (DEVICE_ANDROID, "Android"),
        (DEVICE_IOS, "iOS"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="push_subscriptions",
    )
    endpoint = models.URLField(unique=True)
    p256dh = models.CharField(max_length=255)
    auth = models.CharField(max_length=255)
    device_type = models.CharField(max_length=20, choices=DEVICE_CHOICES, default=DEVICE_WEB)
    user_agent = models.CharField(max_length=512, blank=True, default="")
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "is_active"]),
        ]

    def __str__(self):
        return f"Push subscription for {self.user} ({self.device_type})"

    def as_subscription_info(self):
        return {
            "endpoint": self.endpoint,
            "keys": {
                "p256dh": self.p256dh,
                "auth": self.auth,
            },
        }

