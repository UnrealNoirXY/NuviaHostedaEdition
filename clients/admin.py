from django.contrib import admin
from .models import Company, Structure, StructureRole, StructureMembership

# Unregister the model if it was registered elsewhere, then re-register it.
# This can help in complex setups or when auto-discovery is behaving unexpectedly.
if admin.site.is_registered(Company):
    admin.site.unregister(Company)

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    search_fields = ['name']
    list_display = ('name', 'is_active', 'logo')
    fieldsets = (
        (None, {
            'fields': ('name', 'logo', 'is_active')
        }),
    )


@admin.register(Structure)
class StructureAdmin(admin.ModelAdmin):
    list_display = ("name", "company", "timezone", "is_active")
    list_filter = ("company", "is_active")
    search_fields = ("name", "company__name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    fieldsets = (
        (None, {
            "fields": ("company", "name", "slug", "description", "address"),
        }),
        ("Impostazioni", {
            "fields": ("timezone", "is_active"),
        }),
    )


@admin.register(StructureRole)
class StructureRoleAdmin(admin.ModelAdmin):
    list_display = ("name", "company", "can_edit_layouts", "can_publish_menu")
    list_filter = ("company", "can_publish_menu", "can_edit_layouts")
    search_fields = ("name", "company__name")


@admin.register(StructureMembership)
class StructureMembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "structure", "role", "is_active", "valid_from", "valid_to")
    list_filter = ("structure__company", "is_active", "role")
    search_fields = ("user__username", "structure__name")
    autocomplete_fields = ("user", "structure", "role")
