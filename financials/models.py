import calendar
from datetime import date

from django.conf import settings
from django.db import models
from django.utils import timezone


class FinancialCategory(models.Model):
    """Categoria economica per raggruppare ricavi e costi."""

    TYPE_REVENUE = 'revenue'
    TYPE_COST = 'cost'

    CATEGORY_TYPE_CHOICES = [
        (TYPE_REVENUE, 'Ricavo'),
        (TYPE_COST, 'Costo'),
    ]

    company = models.ForeignKey(
        'clients.Company',
        on_delete=models.CASCADE,
        related_name='financial_categories',
        null=True,
        blank=True,
        help_text="Società di riferimento per la categoria (opzionale per categorie globali).",
    )
    name = models.CharField(max_length=150)
    category_type = models.CharField(max_length=20, choices=CATEGORY_TYPE_CHOICES)
    description = models.TextField(blank=True)
    color = models.CharField(
        max_length=20,
        blank=True,
        help_text="Colore per grafici/dashboard (es. 'primary', '#0d6efd').",
    )
    purchase_category = models.ForeignKey(
        'purchase_orders.PurchaseCategory',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='financial_categories',
        help_text="Collega la categoria al catalogo acquisti per insight automatici.",
    )
    economato_category = models.ForeignKey(
        'economato.EconomatoCategory',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='financial_categories',
        help_text="Collega la categoria all'economato per la lettura dei budget di reparto.",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Categoria Finanziaria"
        verbose_name_plural = "Categorie Finanziarie"
        ordering = ['name']
        unique_together = ('company', 'name', 'category_type')

    def __str__(self):
        return f"{self.name} ({self.get_category_type_display()})"


class FinancialPeriod(models.Model):
    """Rappresenta un periodo di analisi per budget/consuntivo."""

    PERIOD_MONTHLY = 'monthly'
    PERIOD_QUARTERLY = 'quarterly'
    PERIOD_YEARLY = 'yearly'

    PERIOD_CHOICES = [
        (PERIOD_MONTHLY, 'Mensile'),
        (PERIOD_QUARTERLY, 'Trimestrale'),
        (PERIOD_YEARLY, 'Annuale'),
    ]

    company = models.ForeignKey(
        'clients.Company',
        on_delete=models.CASCADE,
        related_name='financial_periods',
        help_text="Società a cui appartiene il periodo.",
    )
    resort = models.ForeignKey(
        'resort.Resort',
        on_delete=models.SET_NULL,
        related_name='financial_periods',
        null=True,
        blank=True,
        help_text="Resort specifico del periodo (opzionale per viste aggregate).",
    )
    period_type = models.CharField(max_length=20, choices=PERIOD_CHOICES, default=PERIOD_MONTHLY)
    year = models.PositiveIntegerField()
    month = models.PositiveSmallIntegerField(null=True, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    is_locked = models.BooleanField(
        default=False,
        help_text="Blocca il periodo per evitare modifiche accidentali ai dati contabilizzati.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Periodo Finanziario"
        verbose_name_plural = "Periodi Finanziari"
        ordering = ['-year', '-month']
        unique_together = ('company', 'resort', 'period_type', 'year', 'month')

    def __str__(self):
        label = self.label
        if self.resort:
            return f"{label} - {self.resort.name}"
        return label

    @property
    def label(self):
        if self.period_type == self.PERIOD_YEARLY:
            return f"Anno {self.year}"
        if self.period_type == self.PERIOD_QUARTERLY and self.month:
            quarter = (int(self.month) - 1) // 3 + 1
            return f"Q{quarter} {self.year}"
        if self.month:
            return timezone.datetime(self.year, self.month, 1).strftime('%B %Y').capitalize()
        return str(self.year)

    def save(self, *args, **kwargs):
        if not self.start_date or not self.end_date:
            if self.period_type == self.PERIOD_MONTHLY and self.month:
                last_day = calendar.monthrange(self.year, self.month)[1]
                self.start_date = date(self.year, self.month, 1)
                self.end_date = date(self.year, self.month, last_day)
            elif self.period_type == self.PERIOD_QUARTERLY and self.month:
                quarter_index = ((self.month - 1) // 3) * 3 + 1
                last_month = quarter_index + 2
                last_day = calendar.monthrange(self.year, last_month)[1]
                self.start_date = date(self.year, quarter_index, 1)
                self.end_date = date(self.year, last_month, last_day)
            elif self.period_type == self.PERIOD_YEARLY:
                self.start_date = date(self.year, 1, 1)
                self.end_date = date(self.year, 12, 31)
        super().save(*args, **kwargs)


class FinancialDataSource(models.Model):
    """Descrive una sorgente dati per importazioni automatiche."""

    SOURCE_MANUAL = 'manual'
    SOURCE_API = 'api'
    SOURCE_FILE = 'file'

    SOURCE_TYPE_CHOICES = [
        (SOURCE_MANUAL, 'Inserimento Manuale'),
        (SOURCE_API, 'Integrazione API'),
        (SOURCE_FILE, 'Importazione File'),
    ]

    company = models.ForeignKey(
        'clients.Company',
        on_delete=models.CASCADE,
        related_name='financial_data_sources',
        null=True,
        blank=True,
        help_text="Società che utilizza la sorgente dati (opzionale per sorgenti condivise).",
    )
    name = models.CharField(max_length=150)
    source_type = models.CharField(max_length=20, choices=SOURCE_TYPE_CHOICES, default=SOURCE_MANUAL)
    description = models.TextField(blank=True)
    configuration = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Sorgente Dati Finanziaria"
        verbose_name_plural = "Sorgenti Dati Finanziarie"
        ordering = ['name']

    def __str__(self):
        return self.name


class FinancialImportBatch(models.Model):
    """Log dei job di importazione da sorgenti esterne."""

    STATUS_PENDING = 'pending'
    STATUS_SUCCESS = 'success'
    STATUS_FAILED = 'failed'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'In Elaborazione'),
        (STATUS_SUCCESS, 'Completato'),
        (STATUS_FAILED, 'Fallito'),
    ]

    data_source = models.ForeignKey(
        FinancialDataSource,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='import_batches',
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='financial_import_batches',
    )
    started_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    imported_records = models.PositiveIntegerField(default=0)
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = "Batch Importazione Finanziaria"
        verbose_name_plural = "Batch Importazione Finanziaria"
        ordering = ['-started_at']

    def __str__(self):
        base = f"Import {self.started_at:%d/%m/%Y %H:%M}"
        if self.data_source:
            return f"{base} - {self.data_source.name}"
        return base


class FinancialSnapshot(models.Model):
    """Contiene i valori aggregati di budget/consuntivo per un periodo."""

    TYPE_BUDGET = 'budget'
    TYPE_ACTUAL = 'actual'
    TYPE_PREVIOUS = 'previous_year'
    TYPE_FORECAST = 'forecast'

    SNAPSHOT_TYPE_CHOICES = [
        (TYPE_BUDGET, 'Budget'),
        (TYPE_ACTUAL, 'Consuntivo'),
        (TYPE_PREVIOUS, 'Anno Precedente'),
        (TYPE_FORECAST, 'Previsione'),
    ]

    period = models.ForeignKey(
        FinancialPeriod,
        on_delete=models.CASCADE,
        related_name='snapshots',
    )
    snapshot_type = models.CharField(max_length=20, choices=SNAPSHOT_TYPE_CHOICES)
    total_revenue = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    total_costs = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    currency = models.CharField(max_length=8, default='EUR')
    notes = models.TextField(blank=True)
    data_source = models.ForeignKey(
        FinancialDataSource,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='snapshots',
    )
    import_batch = models.ForeignKey(
        FinancialImportBatch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='snapshots',
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='financial_snapshots',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Snapshot Finanziario"
        verbose_name_plural = "Snapshot Finanziari"
        ordering = ['-period__year', '-period__month', 'snapshot_type']
        unique_together = ('period', 'snapshot_type')

    def __str__(self):
        return f"{self.period} - {self.get_snapshot_type_display()}"

    @property
    def gross_margin(self):
        return (self.total_revenue or 0) - (self.total_costs or 0)

    @property
    def margin_percentage(self):
        revenue = self.total_revenue or 0
        if revenue == 0:
            return 0
        return (self.gross_margin / revenue) * 100

    def recalculate_totals(self, save=True):
        """Ricalcola i totali sulla base delle righe di dettaglio."""
        aggregates = self.line_items.values('line_type').annotate(total=models.Sum('amount'))
        revenue_total = 0
        cost_total = 0
        for aggregate in aggregates:
            if aggregate['line_type'] == FinancialLineItem.LINE_REVENUE:
                revenue_total = aggregate['total'] or 0
            elif aggregate['line_type'] == FinancialLineItem.LINE_COST:
                cost_total = aggregate['total'] or 0
        self.total_revenue = revenue_total
        self.total_costs = cost_total
        if save:
            self.save(update_fields=['total_revenue', 'total_costs', 'updated_at'])
        return revenue_total, cost_total


class FinancialLineItem(models.Model):
    """Dettaglio di ricavi/costi collegati ad uno snapshot."""

    LINE_REVENUE = 'revenue'
    LINE_COST = 'cost'

    LINE_TYPE_CHOICES = [
        (LINE_REVENUE, 'Ricavo'),
        (LINE_COST, 'Costo'),
    ]

    snapshot = models.ForeignKey(
        FinancialSnapshot,
        on_delete=models.CASCADE,
        related_name='line_items',
    )
    category = models.ForeignKey(
        FinancialCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='line_items',
    )
    line_type = models.CharField(max_length=20, choices=LINE_TYPE_CHOICES, default=LINE_COST)
    description = models.CharField(max_length=255, blank=True)
    amount = models.DecimalField(max_digits=16, decimal_places=2)
    cost_center = models.ForeignKey(
        'economato.EconomatoCostCenter',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='financial_line_items',
    )
    budget = models.ForeignKey(
        'purchase_orders.Budget',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='financial_line_items',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Voce di Dettaglio Finanziaria"
        verbose_name_plural = "Voci di Dettaglio Finanziarie"
        ordering = ['-created_at']

    def __str__(self):
        label = self.description or (self.category.name if self.category else '')
        return f"{label} - {self.amount}"

    def save(self, *args, **kwargs):
        if self.category and not self.line_type:
            self.line_type = self.category.category_type
        super().save(*args, **kwargs)
        self.snapshot.recalculate_totals(save=True)

    def delete(self, *args, **kwargs):
        snapshot = self.snapshot
        super().delete(*args, **kwargs)
        snapshot.recalculate_totals(save=True)

