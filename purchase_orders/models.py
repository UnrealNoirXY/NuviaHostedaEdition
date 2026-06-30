from django.db import models
from django.conf import settings
from resort.models import Resort

from clients.models import Company


class PurchaseCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        verbose_name = "Categoria di Acquisto"
        verbose_name_plural = "Categorie di Acquisto"
        ordering = ['name']

    def __str__(self):
        return self.name

class Supplier(models.Model):
    """
    Represents a supplier or vendor, tied to a specific company.
    """
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='suppliers', verbose_name="Società di Appartenenza", null=True, blank=True)
    name = models.CharField(max_length=255, verbose_name="Nome Fornitore")
    contact_person = models.CharField(max_length=255, blank=True, null=True, verbose_name="Persona di Contatto")
    email = models.EmailField(blank=True, null=True, verbose_name="Email")
    phone_number = models.CharField(max_length=20, blank=True, null=True, verbose_name="Numero di Telefono")
    address = models.TextField(blank=True, null=True, verbose_name="Indirizzo")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Fornitore"
        verbose_name_plural = "Fornitori"
        ordering = ['name']

class PurchaseOrder(models.Model):
    """
    Represents a purchase order, which is a request to a supplier to buy products.
    """
    STATUS_CHOICES = [
        ('draft', 'Bozza'),
        ('submitted', 'Inviato'),
        ('approved', 'Approvato'),
        ('completed', 'Completato'),
        ('cancelled', 'Annullato'),
    ]

    resort = models.ForeignKey(Resort, on_delete=models.CASCADE, related_name='purchase_orders', verbose_name="Resort")
    category = models.ForeignKey(PurchaseCategory, on_delete=models.PROTECT, related_name='purchase_orders', verbose_name="Categoria", null=True, blank=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name='purchase_orders', verbose_name="Fornitore")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='purchase_orders_created', verbose_name="Creato da")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', verbose_name="Stato")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Data Creazione")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Ultima Modifica")

    def __str__(self):
        return f"Ordine #{self.id} per {self.resort.name}"

    @property
    def total_amount(self):
        """Calculates the total amount of the purchase order from its items."""
        return sum(item.total_price for item in self.items.all())

    class Meta:
        verbose_name = "Buono d'Ordine"
        verbose_name_plural = "Buoni d'Ordine"
        ordering = ['-created_at']

class PurchaseOrderItem(models.Model):
    """
    Represents a single item within a purchase order.
    """
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='items', verbose_name="Buono d'Ordine")
    product_name = models.CharField(max_length=255, verbose_name="Nome Prodotto")
    product_code = models.CharField(max_length=100, blank=True, null=True, verbose_name="Codice Prodotto")
    quantity = models.PositiveIntegerField(verbose_name="Quantità")
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Prezzo Unitario")

    @property
    def total_price(self):
        """Calculates the total price for this line item."""
        if self.quantity is not None and self.unit_price is not None:
            return self.quantity * self.unit_price
        return 0

    def __str__(self):
        return f"{self.quantity} x {self.product_name} per Ordine #{self.purchase_order.id}"

    class Meta:
        verbose_name = "Articolo Buono d'Ordine"
        verbose_name_plural = "Articoli Buoni d'Ordine"

class Budget(models.Model):
    """
    Represents the budget allocated to a resort for a specific month and year.
    """
    resort = models.ForeignKey(Resort, on_delete=models.CASCADE, related_name='budgets', verbose_name="Resort")
    category = models.ForeignKey(PurchaseCategory, on_delete=models.CASCADE, related_name='budgets', verbose_name="Categoria", null=True, blank=True)
    year = models.PositiveIntegerField(verbose_name="Anno")
    month = models.PositiveIntegerField(verbose_name="Mese", choices=[(i, i) for i in range(1, 13)])
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Importo Budget")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        category_name = f" - {self.category.name}" if self.category else ""
        return f"Budget per {self.resort.name}{category_name} - {self.month}/{self.year}: €{self.amount}"

    class Meta:
        verbose_name = "Budget"
        verbose_name_plural = "Budget"
        ordering = ['-year', '-month', 'resort', 'category']
        unique_together = ('resort', 'year', 'month', 'category')
