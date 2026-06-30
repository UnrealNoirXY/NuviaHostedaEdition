from django.contrib import admin

from .models import (
    FinancialCategory,
    FinancialPeriod,
    FinancialSnapshot,
    FinancialLineItem,
    FinancialDataSource,
    FinancialImportBatch,
)


class FinancialLineItemInline(admin.TabularInline):
    model = FinancialLineItem
    extra = 0
    autocomplete_fields = ['category', 'cost_center', 'budget']


@admin.register(FinancialSnapshot)
class FinancialSnapshotAdmin(admin.ModelAdmin):
    list_display = (
        'period',
        'snapshot_type',
        'total_revenue',
        'total_costs',
        'gross_margin',
        'data_source',
        'updated_at',
    )
    list_filter = ('snapshot_type', 'period__period_type', 'period__year', 'period__company')
    search_fields = ('period__company__name', 'period__resort__name', 'notes')
    autocomplete_fields = ['period', 'data_source', 'import_batch']
    inlines = [FinancialLineItemInline]


@admin.register(FinancialPeriod)
class FinancialPeriodAdmin(admin.ModelAdmin):
    list_display = ('label', 'company', 'resort', 'period_type', 'year', 'month', 'is_locked')
    list_filter = ('period_type', 'year', 'company')
    search_fields = ('company__name', 'resort__name')
    autocomplete_fields = ['company', 'resort']


@admin.register(FinancialCategory)
class FinancialCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'category_type', 'company', 'is_active')
    list_filter = ('category_type', 'company', 'is_active')
    search_fields = ('name',)
    autocomplete_fields = ['company', 'purchase_category', 'economato_category']


@admin.register(FinancialDataSource)
class FinancialDataSourceAdmin(admin.ModelAdmin):
    list_display = ('name', 'source_type', 'company', 'is_active', 'updated_at')
    list_filter = ('source_type', 'is_active', 'company')
    search_fields = ('name', 'description')
    autocomplete_fields = ['company']


@admin.register(FinancialImportBatch)
class FinancialImportBatchAdmin(admin.ModelAdmin):
    list_display = ('data_source', 'status', 'started_at', 'completed_at', 'imported_records')
    list_filter = ('status', 'data_source__company')
    search_fields = ('notes',)
    autocomplete_fields = ['data_source', 'created_by']

