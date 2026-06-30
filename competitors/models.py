from django.db import models
from clients.models import Company
from resort.models import Resort
from reviews.models import ReviewSource


class Competitor(models.Model):
    """
    Represents a competitor structure.
    """
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='competitors',
        verbose_name="Società di appartenenza"
    )
    name = models.CharField(
        max_length=255,
        verbose_name="Nome Competitor"
    )
    website = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name="Sito Web"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Data di Creazione"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Data di Aggiornamento"
    )

    class Meta:
        verbose_name = "Competitor"
        verbose_name_plural = "Competitors"
        ordering = ['name']
        unique_together = ('company', 'name')

    def __str__(self):
        return self.name


class ScrapingLink(models.Model):
    """
    Represents a specific URL to be scraped for a competitor.
    """
    competitor = models.ForeignKey(
        Competitor,
        on_delete=models.CASCADE,
        related_name='scraping_links'
    )
    source = models.ForeignKey(
        ReviewSource,
        on_delete=models.PROTECT, # Don't allow deleting a source if it's in use
        related_name='competitor_scraping_links',
        verbose_name="Piattaforma di Scraping"
    )
    url = models.URLField(
        max_length=1024,
        verbose_name="URL da Scansionare"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Attivo"
    )
    platform_options = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Opzioni Piattaforma",
        help_text="Es. {\"max_reviews\": 50}. Le opzioni verranno passate all'attore Apify."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Link di Scraping"
        verbose_name_plural = "Link di Scraping"
        ordering = ['competitor', 'source']
        unique_together = ('competitor', 'url')

    def __str__(self):
        return f"{self.competitor.name} - {self.source.name}"


class ResortCompetitorAssociation(models.Model):
    """
    Maps a Competitor to a Resort, creating a many-to-many relationship.
    This defines which competitors are monitored for a given resort.
    """
    resort = models.ForeignKey(
        Resort,
        on_delete=models.CASCADE,
        related_name='competitor_associations'
    )
    competitor = models.ForeignKey(
        Competitor,
        on_delete=models.CASCADE,
        related_name='resort_associations'
    )
    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        verbose_name = "Associazione Resort-Competitor"
        verbose_name_plural = "Associazioni Resort-Competitor"
        unique_together = ('resort', 'competitor')

    def __str__(self):
        return f"{self.resort.name} -> {self.competitor.name}"


class ScrapedData(models.Model):
    """
    Stores a single piece of data scraped from a competitor's website.
    This could be a review, a price point, room availability, etc.
    """
    scraping_link = models.ForeignKey(
        ScrapingLink,
        on_delete=models.CASCADE,
        related_name='scraped_data',
        verbose_name="Link di Origine"
    )
    source_identifier = models.CharField(
        max_length=255,
        db_index=True,
        verbose_name="ID della Fonte"
    )
    data_type = models.CharField(
        max_length=50,
        default='review', # Default type, can be 'price', 'availability', etc.
        verbose_name="Tipo di Dato"
    )
    title = models.CharField(
        max_length=512,
        blank=True,
        null=True,
        verbose_name="Titolo"
    )
    text = models.TextField(
        blank=True,
        null=True,
        verbose_name="Testo"
    )
    rating = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        blank=True,
        null=True,
        verbose_name="Rating"
    )
    author = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Autore"
    )
    publication_date = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Data di Pubblicazione"
    )
    raw_data = models.JSONField(
        default=dict,
        verbose_name="Dati Grezzi (JSON)"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Data di Acquisizione"
    )

    class Meta:
        verbose_name = "Dato Scansionato"
        verbose_name_plural = "Dati Scansionati"
        ordering = ['-publication_date', '-created_at']
        unique_together = ('scraping_link', 'source_identifier')

    def __str__(self):
        return f"Dato da {self.scraping_link.competitor.name} - {self.publication_date.strftime('%Y-%m-%d') if self.publication_date else ''}"


class CompetitorDataAnalysis(models.Model):
    """
    Stores the results of sentiment analysis for a piece of scraped competitor data.
    """
    SENTIMENT_CHOICES = [
        ('positive', 'Positive'),
        ('neutral', 'Neutral'),
        ('negative', 'Negative'),
    ]

    scraped_data = models.OneToOneField(
        ScrapedData,
        on_delete=models.CASCADE,
        related_name='analysis'
    )
    sentiment_score = models.FloatField(help_text="Sentiment score from -1 (very negative) to 1 (very positive)")
    sentiment_label = models.CharField(max_length=10, choices=SENTIMENT_CHOICES, help_text="Categorical label for the sentiment")
    analyzed_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Analysis for Scraped Data ID {self.scraped_data.id} ({self.get_sentiment_label_display()})"
