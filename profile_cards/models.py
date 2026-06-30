from django.conf import settings
from django.db import models
from django.utils import timezone


class CardTemplate(models.Model):
    FONT_CHOICES = [
        ("Inter", "Inter (Modern)"),
        ("Roboto", "Roboto (Standard)"),
        ("Montserrat", "Montserrat (Elegant)"),
        ("Playfair Display", "Playfair (Classic)"),
    ]
    BUTTON_STYLES = [
        ("filled", "Filled"),
        ("outline", "Outline"),
        ("soft", "Soft / Glass"),
    ]
    LAYOUT_CHOICES = [
        ("executive", "Executive (Professional Focus)"),
        ("creative", "Creative (Visual/Social Focus)"),
        ("minimal", "Minimalist (Pure Typography)"),
    ]
    PATTERN_CHOICES = [
        ("none", "None"),
        ("grain", "Film Grain"),
        ("mesh", "Soft Mesh"),
        ("silk", "Luxury Silk Texture"),
    ]

    name = models.CharField(max_length=120, unique=True)
    company_name = models.CharField(max_length=150, blank=True)
    primary_color = models.CharField(max_length=16, default="#111111")
    secondary_color = models.CharField(max_length=16, default="#ffffff")
    font_family = models.CharField(max_length=40, choices=FONT_CHOICES, default="Inter")
    border_radius = models.CharField(max_length=16, default="12px")
    button_style = models.CharField(max_length=20, choices=BUTTON_STYLES, default="filled")
    header_image = models.ImageField(upload_to="profile_cards/headers/", null=True, blank=True)
    header_gradient_enabled = models.BooleanField(default=False)
    layout_type = models.CharField(max_length=32, choices=LAYOUT_CHOICES, default="executive")
    background_pattern = models.CharField(max_length=32, choices=PATTERN_CHOICES, default="none")
    version = models.PositiveIntegerField(default=1)
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class ProfileCardSettings(models.Model):
    singleton_key = models.CharField(max_length=32, unique=True, default="default")
    default_token_days = models.PositiveSmallIntegerField(default=90)
    require_phone = models.BooleanField(default=False)
    require_department = models.BooleanField(default=False)
    auto_update_wallet_passes = models.BooleanField(default=False)
    enable_multi_brand_templates = models.BooleanField(default=False)
    show_apple_wallet = models.BooleanField(default=True)
    show_google_wallet = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(singleton_key="default")
        return obj


class ProfileCard(models.Model):
    STATUS_DRAFT = "draft"
    STATUS_PUBLISHED = "published"
    STATUS_REVOKED = "revoked"
    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_PUBLISHED, "Published"),
        (STATUS_REVOKED, "Revoked"),
    ]

    template = models.ForeignKey(CardTemplate, null=True, blank=True, on_delete=models.SET_NULL, related_name="cards")
    applied_template_version = models.PositiveIntegerField(default=1)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    role = models.CharField(max_length=150)
    email = models.EmailField()
    phone = models.CharField(max_length=40, blank=True)
    department = models.CharField(max_length=120, blank=True)
    linkedin_url = models.URLField(blank=True)
    whatsapp_number = models.CharField(max_length=40, blank=True)
    website_url = models.URLField(blank=True)
    bio = models.TextField(blank=True, max_length=500)
    avatar = models.ImageField(upload_to="profile_cards/avatars/", null=True, blank=True)

    skills = models.CharField(max_length=255, blank=True, help_text="Comma separated skills")
    cta_text = models.CharField(max_length=50, blank=True)
    cta_url = models.URLField(blank=True)
    enable_lead_capture = models.BooleanField(default=False)

    # Visibility controls
    show_apple_wallet = models.BooleanField(default=True)
    show_google_wallet = models.BooleanField(default=True)
    show_linkedin = models.BooleanField(default=True)
    show_whatsapp = models.BooleanField(default=True)
    show_website = models.BooleanField(default=True)

    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["last_name", "first_name"]

    def __str__(self):
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def whatsapp_number_cleaned(self):
        if not self.whatsapp_number:
            return ""
        return "".join(filter(str.isdigit, self.whatsapp_number))

    @property
    def skills_list(self):
        if not self.skills:
            return []
        return [s.strip() for s in self.skills.split(",") if s.strip()]


class ProfileCardPublicToken(models.Model):
    card = models.ForeignKey(ProfileCard, on_delete=models.CASCADE, related_name="public_tokens")
    token = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True, blank=True)
    open_count = models.PositiveIntegerField(default=0)
    share_count = models.PositiveIntegerField(default=0)
    wallet_add_count = models.PositiveIntegerField(default=0)
    vcard_download_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_valid(self):
        return self.revoked_at is None and self.expires_at > timezone.now()


class ProfileCardDelivery(models.Model):
    STATUS_PENDING = "pending"
    STATUS_SENT = "sent"
    STATUS_BOUNCED = "bounced"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_SENT, "Sent"),
        (STATUS_BOUNCED, "Bounced"),
        (STATUS_FAILED, "Failed"),
    ]

    card = models.ForeignKey(ProfileCard, on_delete=models.CASCADE, related_name="deliveries")
    recipient_email = models.EmailField()
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_PENDING)
    attempts = models.PositiveSmallIntegerField(default=0)
    last_error = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="profile_card_deliveries",
    )
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class ProfileCardEvent(models.Model):
    EVENT_OPEN = "open"
    EVENT_SHARE = "share"
    EVENT_ADD_WALLET = "add_wallet"
    EVENT_VCARD = "vcard_download"
    EVENT_CHOICES = [
        (EVENT_OPEN, "Open"),
        (EVENT_SHARE, "Share"),
        (EVENT_ADD_WALLET, "Add Wallet"),
        (EVENT_VCARD, "Vcard Download"),
    ]

    card = models.ForeignKey(ProfileCard, on_delete=models.CASCADE, related_name="events")
    token = models.ForeignKey(ProfileCardPublicToken, null=True, blank=True, on_delete=models.SET_NULL, related_name="events")
    event_type = models.CharField(max_length=32, choices=EVENT_CHOICES)
    source = models.CharField(max_length=64, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)
    ip_hash = models.CharField(max_length=128, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["event_type", "created_at"])]


class ProfileCardLead(models.Model):
    card = models.ForeignKey(ProfileCard, on_delete=models.CASCADE, related_name="leads")
    name = models.CharField(max_length=150)
    email = models.EmailField()
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Message from {self.name} for {self.card}"
