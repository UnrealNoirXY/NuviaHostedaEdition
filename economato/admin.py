from django.contrib import admin
from . import models


@admin.register(models.EconomatoCategory)
class EconomatoCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'company', 'color', 'created_at')
    search_fields = ('name', 'company__name')
    list_filter = ('company',)


@admin.register(models.EconomatoCostCenter)
class EconomatoCostCenterAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'company', 'is_active')
    search_fields = ('code', 'name', 'company__name')
    list_filter = ('company', 'is_active')


class EconomatoRequestItemInline(admin.TabularInline):
    model = models.EconomatoRequestItem
    extra = 0


@admin.register(models.EconomatoItem)
class EconomatoItemAdmin(admin.ModelAdmin):
    list_display = (
        'code',
        'name',
        'company',
        'resort',
        'category',
        'unit',
        'reorder_point',
        'optimal_stock',
        'is_active',
    )
    search_fields = ('code', 'name', 'description', 'company__name', 'resort__name')
    list_filter = ('company', 'resort', 'category', 'is_active')


@admin.register(models.EconomatoStockLevel)
class EconomatoStockLevelAdmin(admin.ModelAdmin):
    list_display = ('item', 'resort', 'quantity', 'reserved_quantity', 'updated_at')
    list_filter = ('resort', 'item__category', 'item__company')
    search_fields = ('item__name', 'resort__name')


@admin.register(models.EconomatoRequest)
class EconomatoRequestAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'company',
        'resort',
        'status',
        'priority',
        'total_estimated_cost',
        'created_at',
        'requested_by',
        'approved_by',
    )
    list_filter = ('status', 'priority', 'company', 'resort')
    search_fields = ('id', 'resort__name', 'requested_by__username')
    inlines = [EconomatoRequestItemInline]


@admin.register(models.EconomatoTimelineEvent)
class EconomatoTimelineEventAdmin(admin.ModelAdmin):
    list_display = ('request', 'verb', 'created_at', 'created_by')
    list_filter = ('verb', 'created_at')
    search_fields = ('request__id', 'verb', 'created_by__username')


@admin.register(models.EconomatoRequestItem)
class EconomatoRequestItemAdmin(admin.ModelAdmin):
    list_display = ('request', 'description', 'quantity', 'unit_cost', 'supplier')
    search_fields = ('description', 'request__id', 'supplier__name')
    list_filter = ('supplier',)
