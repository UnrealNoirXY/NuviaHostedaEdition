from django.contrib import admin
from .models import Asset, AssetCategory

@admin.register(AssetCategory)
class AssetCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)

@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'serial_number', 'resort', 'purchase_date')
    list_filter = ('category', 'resort', 'purchase_date', 'warranty_expiry_date')
    search_fields = ('name', 'serial_number', 'resort__name', 'notes')
