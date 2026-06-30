from django.conf import settings
from django.db import models
from django.utils import timezone


class EconomatoCategory(models.Model):
    """Categoria merceologica gestita dall'economato."""

    company = models.ForeignKey(
        'clients.Company',
        on_delete=models.CASCADE,
        related_name='economato_categories',
        null=True,
        blank=True,
        help_text="Società proprietaria della categoria."
    )
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    color = models.CharField(
        max_length=20,
        blank=True,
        help_text="Colore personalizzato per dashboard e tagging (es. 'primary', '#FF8800')."
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Categoria Economato"
        verbose_name_plural = "Categorie Economato"
        unique_together = ('company', 'name')
        ordering = ['name']

    def __str__(self):
        return self.name


class EconomatoCostCenter(models.Model):
    """Centri di costo associati alle richieste di economato."""

    company = models.ForeignKey(
        'clients.Company',
        on_delete=models.CASCADE,
        related_name='economato_cost_centers'
    )
    code = models.CharField(max_length=50)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Centro di costo Economato"
        verbose_name_plural = "Centri di costo Economato"
        unique_together = ('company', 'code')
        ordering = ['code']

    def __str__(self):
        return f"{self.code} - {self.name}"


class EconomatoItem(models.Model):
    """Articolo gestito all'interno dell'app di economato."""

    UNIT_CHOICES = [
        ('pz', 'Pezzi'),
        ('kg', 'Chilogrammi'),
        ('lt', 'Litri'),
        ('box', 'Box'),
        ('set', 'Set'),
    ]

    company = models.ForeignKey(
        'clients.Company',
        on_delete=models.CASCADE,
        related_name='economato_items',
        help_text="Società proprietaria dell'articolo."
    )
    resort = models.ForeignKey(
        'resort.Resort',
        on_delete=models.SET_NULL,
        related_name='economato_items',
        null=True,
        blank=True,
        help_text="Resort specifico a cui è dedicato l'articolo (opzionale)."
    )
    category = models.ForeignKey(
        EconomatoCategory,
        on_delete=models.SET_NULL,
        related_name='items',
        null=True,
        blank=True
    )
    supplier = models.ForeignKey(
        'purchase_orders.Supplier',
        on_delete=models.SET_NULL,
        related_name='economato_items',
        null=True,
        blank=True
    )
    code = models.CharField(max_length=80)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    unit = models.CharField(max_length=10, choices=UNIT_CHOICES, default='pz')
    reorder_point = models.PositiveIntegerField(default=0, help_text="Livello minimo di scorta prima del riordino.")
    optimal_stock = models.PositiveIntegerField(default=0, help_text="Livello ottimale di scorta per l'articolo.")
    last_purchase_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='economato_items_created',
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Articolo Economato"
        verbose_name_plural = "Articoli Economato"
        unique_together = ('company', 'code')
        ordering = ['name']

    def __str__(self):
        return f"{self.code} - {self.name}"


class EconomatoStockLevel(models.Model):
    """Giacenza di un articolo per resort."""

    item = models.ForeignKey(EconomatoItem, on_delete=models.CASCADE, related_name='stock_levels')
    resort = models.ForeignKey('resort.Resort', on_delete=models.CASCADE, related_name='economato_stock_levels')
    quantity = models.PositiveIntegerField(default=0)
    reserved_quantity = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='economato_stock_updates',
        null=True,
        blank=True
    )

    class Meta:
        verbose_name = "Giacenza Economato"
        verbose_name_plural = "Giacenze Economato"
        unique_together = ('item', 'resort')

    @property
    def available_quantity(self):
        return max(self.quantity - self.reserved_quantity, 0)

    def is_below_reorder(self):
        reorder_point = self.item.reorder_point or 0
        return self.available_quantity <= reorder_point

    def __str__(self):
        return f"{self.item.name} @ {self.resort.name}: {self.quantity}"


class EconomatoRequest(models.Model):
    """Richiesta di approvvigionamento economato con workflow multi-ruolo."""

    STATUS_DRAFT = 'draft'
    STATUS_PENDING = 'pending'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED = 'rejected'
    STATUS_FULFILLED = 'fulfilled'
    STATUS_CANCELLED = 'cancelled'

    STATUS_CHOICES = [
        (STATUS_DRAFT, 'Bozza'),
        (STATUS_PENDING, 'In Approvazione'),
        (STATUS_APPROVED, 'Approvata'),
        (STATUS_REJECTED, 'Rifiutata'),
        (STATUS_FULFILLED, 'Completata'),
        (STATUS_CANCELLED, 'Annullata'),
    ]

    PRIORITY_LOW = 'low'
    PRIORITY_MEDIUM = 'medium'
    PRIORITY_HIGH = 'high'
    PRIORITY_CRITICAL = 'critical'

    PRIORITY_CHOICES = [
        (PRIORITY_LOW, 'Bassa'),
        (PRIORITY_MEDIUM, 'Media'),
        (PRIORITY_HIGH, 'Alta'),
        (PRIORITY_CRITICAL, 'Critica'),
    ]

    company = models.ForeignKey('clients.Company', on_delete=models.CASCADE, related_name='economato_requests')
    resort = models.ForeignKey('resort.Resort', on_delete=models.CASCADE, related_name='economato_requests')
    cost_center = models.ForeignKey(
        EconomatoCostCenter,
        on_delete=models.SET_NULL,
        related_name='requests',
        null=True,
        blank=True
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='economato_requests_created',
        null=True,
        blank=True
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='economato_requests_approved',
        null=True,
        blank=True
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default=PRIORITY_MEDIUM)
    needed_by = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    total_estimated_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    cancellation_reason = models.TextField(blank=True)

    class Meta:
        verbose_name = "Richiesta Economato"
        verbose_name_plural = "Richieste Economato"
        ordering = ['-created_at']

    def __str__(self):
        return f"Richiesta #{self.pk} - {self.get_status_display()}"

    def recalculate_total(self):
        total = sum(item.total_cost for item in self.items.all())
        self.total_estimated_cost = total
        self.save(update_fields=['total_estimated_cost', 'updated_at'])


class EconomatoRequestItem(models.Model):
    """Articoli richiesti all'interno di una richiesta economato."""

    request = models.ForeignKey(EconomatoRequest, on_delete=models.CASCADE, related_name='items')
    item = models.ForeignKey(EconomatoItem, on_delete=models.SET_NULL, null=True, blank=True, related_name='request_lines')
    description = models.CharField(max_length=255)
    quantity = models.PositiveIntegerField()
    unit_of_measure = models.CharField(max_length=20, blank=True)
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    supplier = models.ForeignKey(
        'purchase_orders.Supplier',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='economato_request_items'
    )

    class Meta:
        verbose_name = "Articolo Richiesta Economato"
        verbose_name_plural = "Articoli Richiesta Economato"

    @property
    def total_cost(self):
        return (self.quantity or 0) * (self.unit_cost or 0)

    def __str__(self):
        return f"{self.description} ({self.quantity})"


class EconomatoTimelineEvent(models.Model):
    """Eventi tracciati per audit trail delle richieste economato."""

    request = models.ForeignKey(EconomatoRequest, on_delete=models.CASCADE, related_name='timeline')
    created_at = models.DateTimeField(default=timezone.now)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='economato_timeline_events'
    )
    verb = models.CharField(max_length=120)
    payload = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = "Evento Timeline Economato"
        verbose_name_plural = "Eventi Timeline Economato"
        ordering = ['created_at']

    def __str__(self):
        return f"{self.created_at:%d/%m/%Y %H:%M} - {self.verb}"
