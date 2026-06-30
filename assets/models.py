from django.db import models
from django.conf import settings

class AssetCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name = "Categoria Asset"
        verbose_name_plural = "Categorie Asset"
        ordering = ['name']

    def __str__(self):
        return self.name

from resort.models import Resort

class Asset(models.Model):
    name = models.CharField(max_length=200)
    category = models.ForeignKey(AssetCategory, on_delete=models.PROTECT, related_name='assets')
    resort = models.ForeignKey(Resort, on_delete=models.SET_NULL, null=True, blank=True, related_name='assets')
    serial_number = models.CharField(max_length=100, blank=True, unique=True, null=True)
    purchase_date = models.DateField(null=True, blank=True)
    purchase_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Costo di Acquisto")
    warranty_expiry_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Asset"
        verbose_name_plural = "Asset"
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.serial_number or 'N/A'})"
