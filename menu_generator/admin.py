from django.contrib import admin

from .models import (
    Allergene,
    Ingrediente,
    BaseFoodItem,
    Piatto,
    LayoutTemplate,
    CavaliereTemplate,
    Menu,
    MenuVersion,
)


@admin.register(Allergene)
class AllergeneAdmin(admin.ModelAdmin):
    list_display = ("codice", "nome", "company", "is_active")
    list_filter = ("company", "is_active")
    search_fields = ("codice", "nome", "descrizione")


@admin.register(Ingrediente)
class IngredienteAdmin(admin.ModelAdmin):
    list_display = ("nome", "company", "stagionalita", "is_active")
    list_filter = ("company", "stagionalita", "is_active")
    search_fields = ("nome", "descrizione")
    autocomplete_fields = ("company",)
    filter_horizontal = ("allergeni",)


@admin.register(BaseFoodItem)
class BaseFoodItemAdmin(admin.ModelAdmin):
    list_display = ("nome", "company", "categoria", "versione", "is_active")
    list_filter = ("company", "categoria", "is_active")
    search_fields = ("nome",)
    filter_horizontal = ("ingredienti_default", "allergeni_default")


class PiattoIngredienteInline(admin.TabularInline):
    model = Piatto.ingredienti.through
    extra = 1
    autocomplete_fields = ("ingrediente",)


@admin.register(Piatto)
class PiattoAdmin(admin.ModelAdmin):
    list_display = ("nome", "categoria", "company", "stagionalita", "is_active")
    list_filter = ("company", "categoria", "stagionalita", "is_active")
    search_fields = ("nome", "descrizione")
    autocomplete_fields = ("company", "base_item", "variante_di")
    filter_horizontal = ("allergeni",)
    inlines = [PiattoIngredienteInline]


@admin.register(LayoutTemplate)
class LayoutTemplateAdmin(admin.ModelAdmin):
    list_display = ("nome_layout", "company", "versione", "data_modifica")
    list_filter = ("company",)
    search_fields = ("nome_layout",)
    autocomplete_fields = ("company", "creato_da")


@admin.register(CavaliereTemplate)
class CavaliereTemplateAdmin(admin.ModelAdmin):
    list_display = ("nome", "company", "layout", "creato_il")
    list_filter = ("company", "layout")
    search_fields = ("nome",)
    autocomplete_fields = ("company", "layout", "creato_da")


class MenuVersionInline(admin.TabularInline):
    model = MenuVersion
    extra = 0
    readonly_fields = ("creato_il", "creato_da", "payload")
    can_delete = False


@admin.register(Menu)
class MenuAdmin(admin.ModelAdmin):
    list_display = ("nome", "company", "struttura", "data_evento", "turno", "is_published")
    list_filter = ("company", "struttura", "turno", "is_published")
    search_fields = ("nome", "ospiti_target")
    autocomplete_fields = ("company", "creato_da", "layout", "cavaliere_template", "struttura")
    filter_horizontal = ("piatti",)
    inlines = [MenuVersionInline]


@admin.register(MenuVersion)
class MenuVersionAdmin(admin.ModelAdmin):
    list_display = ("menu", "creato_il", "creato_da")
    list_filter = ("menu__company",)
    search_fields = ("menu__nome",)
    autocomplete_fields = ("menu", "creato_da")
    readonly_fields = ("payload", "creato_il")
