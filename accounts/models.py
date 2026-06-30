from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.conf import settings

class User(AbstractUser):
    RECEPTIONIST = 'receptionist'
    MAINTAINER = 'maintainer'
    HEAD_MAINTAINER = 'head_maintainer'
    MAINTENANCE_MANAGER = 'maintenance_manager'
    SUPERADMIN = 'superadmin'
    HOUSEKEEPING = 'housekeeping'
    DIRECTOR = 'director'
    OWNER = 'owner'
    CHEF = 'chef'
    ADMINISTRATIVE = 'administrative'
    CORPORATE = 'corporate'
    IT_TECHNICIAN = 'it_technician'
    ECONOMO = 'economo'
    CAPO_ECONOMO = 'capo_economo'
    RISORSE_UMANE = 'risorse_umane'
    ROLE_CHOICES = [
        (RECEPTIONIST, 'Receptionist'),
        (MAINTAINER, 'Manutentore'),
        (HEAD_MAINTAINER, 'Capomanutentore'),
        (MAINTENANCE_MANAGER, 'Responsabile Manutenzione'),
        (HOUSEKEEPING, 'Housekeeping'),
        (DIRECTOR, 'Direttore'),
        (OWNER, 'Proprietario'),
        (CHEF, 'Chef'),
        (ADMINISTRATIVE, 'Amministrativo'),
        (CORPORATE, 'Corporate'),
        (IT_TECHNICIAN, 'Tecnico IT'),
        (SUPERADMIN, 'Super Admin'),
        (ECONOMO, 'Economo'),
        (CAPO_ECONOMO, 'Capo Economo'),
        (RISORSE_UMANE, 'Risorse Umane'),
    ]
    role = models.CharField(max_length=30, choices=ROLE_CHOICES, db_index=True)
    company = models.ForeignKey('clients.Company', on_delete=models.CASCADE, null=True, blank=True, related_name='users', help_text="La società a cui questo utente appartiene.")
    resort = models.ForeignKey('resort.Resort', on_delete=models.SET_NULL, null=True, blank=True)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    last_seen = models.DateTimeField(default=timezone.now)
    gamertag = models.CharField(max_length=20, unique=True, null=True, blank=True, help_text="Nickname univoco per la sezione svago")

    # Tool Permissions
    has_maintenance_access = models.BooleanField(default=True)
    has_reviews_access = models.BooleanField(default=False)
    has_concierge_access = models.BooleanField(default=False)
    can_manage_purchase_orders = models.BooleanField(default=False, verbose_name="Abilita Gestione Buoni d'Ordine", help_text="Se selezionato, l'utente potrà creare e gestire i buoni d'ordine.")
    has_inventory_access = models.BooleanField(default=False, verbose_name="Abilita Gestione Inventario", help_text="Se selezionato, l'utente potrà visualizzare e gestire l'inventario.")
    has_it_support_management_access = models.BooleanField(default=False, verbose_name="Abilita Gestione Supporto IT", help_text="Se selezionato, l'utente potrà gestire i ticket di supporto IT (non solo crearli).")
    can_export_review_reports = models.BooleanField(
        default=False,
        verbose_name="Può Esportare Report Recensioni",
        help_text="Consente all'utente di generare ed esportare report di recensioni in formato PDF."
    )
    menu_creation_studio_enabled = models.BooleanField(
        default=False,
        verbose_name="Abilita Menu Creation Studio",
        help_text="Se selezionato, l'utente potrà accedere allo strumento di creazione menu."
    )
    is_2fa_enabled = models.BooleanField(default=False, verbose_name="Autenticazione a Due Fattori Abilitata")
    password_last_changed = models.DateTimeField(null=True, blank=True, verbose_name="Ultima Modifica Password")

    skills = models.ManyToManyField('skills.Skill', blank=True, related_name='users', verbose_name="Competenze")

    # Personalization settings
    THEME_LIGHT = 'light'
    THEME_DARK = 'dark'
    THEME_AUTO = 'auto'
    THEME_CHOICES = [
        (THEME_LIGHT, 'Chiaro'),
        (THEME_DARK, 'Scuro'),
        (THEME_AUTO, 'Automatico (sistema)'),
    ]
    theme = models.CharField(
        max_length=10,
        choices=THEME_CHOICES,
        default=THEME_AUTO,
        verbose_name="Tema Grafico"
    )
    background_image_desktop = models.ImageField(
        upload_to='user_backgrounds/desktop/',
        null=True,
        blank=True,
        verbose_name="Sfondo Desktop"
    )
    background_image_mobile = models.ImageField(
        upload_to='user_backgrounds/mobile/',
        null=True,
        blank=True,
        verbose_name="Sfondo Mobile"
    )
    fiscal_code = models.CharField(
        max_length=16,
        null=True,
        blank=True,
        db_index=True,
        verbose_name="Codice Fiscale",
        help_text="Codice fiscale dell'utente (16 caratteri).",
    )

    receives_unassigned_ticket_alerts = models.BooleanField(
        default=True,
        help_text="Se disattivato, l'utente non riceverà promemoria sui ticket di manutenzione non assegnati.",
        verbose_name="Riceve avvisi ticket non assegnati",
    )
    must_change_password = models.BooleanField(
        default=False,
        help_text="Se attivo, l'utente deve cambiare la password al primo accesso.",
        verbose_name="Cambio password obbligatorio",
    )

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"


class PrivacyPolicyVersion(models.Model):
    version = models.CharField(max_length=50, unique=True)
    content = models.TextField(help_text="Contenuto HTML/testo della policy.")
    published_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-published_at", "-created_at")
        verbose_name = "Versione Policy Privacy"
        verbose_name_plural = "Versioni Policy Privacy"

    def __str__(self):
        return f"{self.version}{' (attiva)' if self.is_active else ''}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.is_active:
            PrivacyPolicyVersion.objects.exclude(pk=self.pk).filter(is_active=True).update(is_active=False)


class UserPrivacyConsent(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="privacy_consents",
    )
    policy_version = models.ForeignKey(
        PrivacyPolicyVersion,
        on_delete=models.PROTECT,
        related_name="user_consents",
    )
    accepted_at = models.DateTimeField(default=timezone.now)
    payslip_email_opt_in = models.BooleanField(default=False)
    payslip_email_opt_in_at = models.DateTimeField(null=True, blank=True)
    email_confirmed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "policy_version")
        ordering = ("-accepted_at", "-created_at")
        verbose_name = "Consenso Privacy Utente"
        verbose_name_plural = "Consensi Privacy Utenti"
        indexes = [
            models.Index(fields=["user", "policy_version"]),
            models.Index(fields=["payslip_email_opt_in"]),
        ]

    def __str__(self):
        return f"{self.user} · {self.policy_version}"
