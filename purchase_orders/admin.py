from django.contrib import admin
from .models import Supplier, PurchaseOrder, PurchaseOrderItem, PurchaseCategory, Budget

class PurchaseOrderItemInline(admin.TabularInline):
    """
    Allows editing of PurchaseOrderItems directly within the PurchaseOrder admin page.
    """
    model = PurchaseOrderItem
    extra = 1  # Start with one extra form for a new item
    fields = ('product_name', 'product_code', 'quantity', 'unit_price', 'total_price')
    readonly_fields = ('total_price',)
    # autocomplete_fields = ['product_name'] # Could be useful with a Product model in the future

@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    """
    Admin configuration for the Supplier model.
    """
    list_display = ('name', 'contact_person', 'email', 'phone_number', 'created_at')
    search_fields = ('name', 'contact_person', 'email')

@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    """
    Admin configuration for the PurchaseOrder model.
    """
    list_display = ('id', 'resort', 'supplier', 'status', 'created_by', 'created_at', 'total_amount')
    list_filter = ('status', 'resort', 'supplier')
    search_fields = ('id', 'resort__name', 'supplier__name', 'created_by__username')
    readonly_fields = ('created_at', 'updated_at', 'total_amount')
    inlines = [PurchaseOrderItemInline]
    date_hierarchy = 'created_at'

    fieldsets = (
        (None, {
            'fields': ('resort', 'supplier')
        }),
        ('Stato e Assegnazione', {
            'fields': ('status', 'created_by')
        }),
        ('Dettagli Monetari e Date', {
            'fields': ('total_amount', 'created_at', 'updated_at')
        }),
    )

@admin.register(PurchaseOrderItem)
class PurchaseOrderItemAdmin(admin.ModelAdmin):
    """
    Admin configuration for the PurchaseOrderItem model.
    """
    list_display = ('get_order_id', 'product_name', 'quantity', 'unit_price', 'total_price')
    search_fields = ('product_name', 'purchase_order__id')
    readonly_fields = ('total_price',)
    autocomplete_fields = ['purchase_order']

    def get_order_id(self, obj):
        return obj.purchase_order.id
    get_order_id.short_description = "ID Ordine"
    get_order_id.admin_order_field = 'purchase_order__id'


@admin.register(PurchaseCategory)
class PurchaseCategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ('resort', 'category', 'year', 'month', 'amount')
    list_filter = ('resort__company', 'year', 'category')
    search_fields = ('resort__name',)
    autocomplete_fields = ['resort', 'category']
