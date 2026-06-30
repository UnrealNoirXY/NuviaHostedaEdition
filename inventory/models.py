from django.db import models
from resort.models import Resort
from purchase_orders.models import PurchaseOrder

class InventoryItem(models.Model):
    """
    Represents a unique item stored in the inventory for a specific resort.
    """
    resort = models.ForeignKey(Resort, on_delete=models.CASCADE, related_name='inventory_items', verbose_name="Resort")
    name = models.CharField(max_length=255, verbose_name="Nome Articolo")
    product_code = models.CharField(max_length=100, blank=True, null=True, verbose_name="Codice Prodotto/SKU")
    description = models.TextField(blank=True, null=True, verbose_name="Descrizione")
    current_stock = models.PositiveIntegerField(default=0, verbose_name="Giacenza Attuale")

    # To be added later: supplier, min_stock_level, location_in_storage, etc.

    def __str__(self):
        return f"{self.name} ({self.resort.name})"

    class Meta:
        verbose_name = "Articolo in Inventario"
        verbose_name_plural = "Articoli in Inventario"
        unique_together = ('resort', 'product_code')
        ordering = ['resort', 'name']

class StockRecord(models.Model):
    """
    Represents a single transaction that changes the stock level of an inventory item.
    """
    REASON_CHOICES = [
        ('initial', 'Giacenza Iniziale'),
        ('purchase', 'Entrata da Ordine'),
        ('withdrawal', 'Prelievo/Utilizzo'),
        ('adjustment', 'Rettifica Manuale'),
        ('return', 'Reso'),
    ]

    item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE, related_name='stock_records', verbose_name="Articolo")
    change = models.IntegerField(verbose_name="Variazione (+/-)")
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="Data e Ora")
    reason = models.CharField(max_length=20, choices=REASON_CHOICES, verbose_name="Motivo")
    purchase_order = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='stock_records',
        verbose_name="Rif. Buono d'Ordine"
    )
    notes = models.TextField(blank=True, null=True, verbose_name="Note")

    def __str__(self):
        return f"{self.get_reason_display()} di {self.change} per {self.item.name} il {self.timestamp.strftime('%Y-%m-%d')}"

    class Meta:
        verbose_name = "Movimento di Magazzino"
        verbose_name_plural = "Movimenti di Magazzino"
        ordering = ['-timestamp']
