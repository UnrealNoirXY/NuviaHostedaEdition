from django.contrib import admin
from .models import Resort, Room

class RoomInline(admin.TabularInline):
    model = Room
    extra = 1

@admin.register(Resort)
class ResortAdmin(admin.ModelAdmin):
    list_display = ('name', 'location', 'company')
    list_filter = ('company',)
    search_fields = ['name', 'location']
    inlines = [RoomInline]

@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ('name', 'resort', 'description')
    list_filter = ('resort',)
    search_fields = ['name', 'resort__name']
