from django.conf import settings
from django.db import models
from django.utils import timezone

class Company(models.Model):
    name = models.CharField(max_length=255, unique=True, help_text="Il nome della società cliente.")
    logo = models.ImageField(upload_to='company_logos/', null=True, blank=True, help_text="Logo della società, mostrato nei report.")
    is_active = models.BooleanField(default=True, help_text="Indica se l'account della società è attivo.")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']
        verbose_name = "Società"
        verbose_name_plural = "Società"


class Structure(models.Model):
    """Rappresenta una singola struttura (hotel, ristorante, resort) appartenente a una società."""

    name = models.CharField(max_length=255, help_text="Nome pubblico della struttura.")
    slug = models.SlugField(max_length=255, unique=True, help_text="Slug univoco per i collegamenti rapidi.")
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="structures",
        help_text="Società proprietaria della struttura.",
    )
    description = models.TextField(blank=True, help_text="Descrizione breve o note interne sulla struttura.")
    timezone = models.CharField(
        max_length=100,
        default="Europe/Rome",
        help_text="Fuso orario utilizzato per pianificazioni e generazione documenti.",
    )
    address = models.CharField(max_length=255, blank=True, help_text="Indirizzo della struttura.")
    is_active = models.BooleanField(default=True, help_text="Indica se la struttura è operativa.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["company__name", "name"]
        unique_together = ("company", "name")
        verbose_name = "Struttura"
        verbose_name_plural = "Strutture"

    def __str__(self):
        return f"{self.name} ({self.company.name})"


class StructureRole(models.Model):
    """Ruoli granulari per le strutture con permessi specifici per il Menu Creation Studio."""

    name = models.CharField(max_length=150, help_text="Nome del ruolo (es. Chef, Maître).")
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="structure_roles",
        help_text="Società proprietaria del ruolo.",
    )
    can_edit_layouts = models.BooleanField(
        default=False,
        help_text="Può creare e modificare i layout grafici per menu e cavalieri.",
    )
    can_edit_menus = models.BooleanField(
        default=True,
        help_text="Può creare e modificare i menu (dati base e composizione).",
    )
    can_edit_dishes = models.BooleanField(
        default=True,
        help_text="Può creare, aggiornare e cancellare piatti nel catalogo aziendale.",
    )
    can_publish_menu = models.BooleanField(
        default=False,
        help_text="Può pubblicare e generare documenti ufficiali dei menu.",
    )
    can_approve_menu = models.BooleanField(
        default=False,
        help_text="Può approvare menu e versioni prima della pubblicazione.",
    )
    can_manage_allergens = models.BooleanField(
        default=True,
        help_text="Può aggiungere/aggiornare ingredienti e allergeni.",
    )
    can_manage_templates = models.BooleanField(
        default=False,
        help_text="Può creare e modificare template di cavalieri e bundle di documenti.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["company__name", "name"]
        unique_together = ("company", "name")
        verbose_name = "Ruolo Struttura"
        verbose_name_plural = "Ruoli Struttura"

    def __str__(self):
        return f"{self.name} - {self.company.name}"


class StructureMembership(models.Model):
    """Associa un utente a una struttura con un ruolo specifico e permessi temporali."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="structure_memberships",
        help_text="Utente assegnato alla struttura.",
    )
    structure = models.ForeignKey(
        Structure,
        on_delete=models.CASCADE,
        related_name="memberships",
        help_text="Struttura di appartenenza.",
    )
    role = models.ForeignKey(
        StructureRole,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="memberships",
        help_text="Ruolo assegnato all'utente.",
    )
    is_active = models.BooleanField(default=True, help_text="Se disattivato l'utente non può operare nella struttura.")
    valid_from = models.DateField(default=timezone.now, help_text="Data di inizio validità del ruolo.")
    valid_to = models.DateField(null=True, blank=True, help_text="Data di fine validità, opzionale.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["structure__company__name", "structure__name", "user__username"]
        unique_together = ("user", "structure", "role")
        verbose_name = "Membro Struttura"
        verbose_name_plural = "Membri Struttura"

    def __str__(self):
        return f"{self.user} @ {self.structure}"

    @property
    def permissions(self):
        if not self.role:
            return {}
        return {
            "can_edit_layouts": self.role.can_edit_layouts,
            "can_edit_menus": self.role.can_edit_menus,
            "can_edit_dishes": self.role.can_edit_dishes,
            "can_publish_menu": self.role.can_publish_menu,
            "can_approve_menu": self.role.can_approve_menu,
            "can_manage_allergens": self.role.can_manage_allergens,
            "can_manage_templates": self.role.can_manage_templates,
        }
