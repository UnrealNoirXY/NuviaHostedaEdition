from django.contrib import admin
from .models import Review, ReviewSource, ScrapingURL, ReportTemplate, ScheduledScraping, ReviewAnalysis

@admin.register(ReviewSource)
class ReviewSourceAdmin(admin.ModelAdmin):
    list_display = ('name', 'scraper_identifier')
    search_fields = ['name']

@admin.register(ScrapingURL)
class ScrapingURLAdmin(admin.ModelAdmin):
    list_display = ('url', 'resort', 'source')
    list_filter = ('source', 'resort')
    search_fields = ['url', 'resort__name']
    autocomplete_fields = ['resort', 'source']

class ReviewAnalysisInline(admin.StackedInline):
    model = ReviewAnalysis
    can_delete = False
    verbose_name_plural = 'Sentiment Analysis'
    readonly_fields = ('sentiment_label', 'sentiment_score', 'keywords', 'analyzed_at')

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('title', 'resort', 'source', 'rating', 'review_date')
    list_filter = ('source', 'resort', 'review_date')
    search_fields = ('title', 'text', 'author')
    date_hierarchy = 'review_date'
    inlines = [ReviewAnalysisInline]
    readonly_fields = ('created_at',)

@admin.register(ReportTemplate)
class ReportTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'report_type', 'created_at')
    list_filter = ('user', 'report_type')
    search_fields = ['name']

@admin.register(ScheduledScraping)
class ScheduledScrapingAdmin(admin.ModelAdmin):
    list_display = ('name', 'frequency', 'is_active', 'updated_at')
    list_filter = ('is_active', 'frequency')
    search_fields = ['name']
    filter_horizontal = ('resorts', 'sources')
