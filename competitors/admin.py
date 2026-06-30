from django.contrib import admin
from .models import Competitor, ScrapingLink, ResortCompetitorAssociation, ScrapedData

@admin.register(Competitor)
class CompetitorAdmin(admin.ModelAdmin):
    list_display = ('name', 'company', 'website', 'created_at')
    list_filter = ('company',)
    search_fields = ('name', 'website')
    ordering = ('-created_at',)
    autocomplete_fields = ['company']

@admin.register(ScrapingLink)
class ScrapingLinkAdmin(admin.ModelAdmin):
    list_display = ('competitor', 'source', 'url', 'is_active')
    list_filter = ('source', 'is_active', 'competitor__company')
    search_fields = ('competitor__name', 'url')
    autocomplete_fields = ['competitor', 'source']

@admin.register(ResortCompetitorAssociation)
class ResortCompetitorAssociationAdmin(admin.ModelAdmin):
    list_display = ('resort', 'competitor', 'created_at')
    list_filter = ('resort__company',)
    search_fields = ('resort__name', 'competitor__name')
    autocomplete_fields = ['resort', 'competitor']

@admin.register(ScrapedData)
class ScrapedDataAdmin(admin.ModelAdmin):
    list_display = ('scraping_link', 'data_type', 'publication_date', 'rating', 'author')
    list_filter = ('data_type', 'scraping_link__source', 'scraping_link__competitor__company')
    search_fields = ('title', 'text', 'author')
    date_hierarchy = 'publication_date'
    readonly_fields = ('created_at',)
    autocomplete_fields = ['scraping_link']
