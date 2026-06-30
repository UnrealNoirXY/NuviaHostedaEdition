from django.db import models
from django.conf import settings
from resort.models import Resort

class ReviewSource(models.Model):
    """
    Represents the source of a review, e.g., Booking.com, Google Reviews.
    """
    name = models.CharField(max_length=100, unique=True, help_text="Name of the review source (e.g., Booking.com)")
    base_url = models.URLField(max_length=255, blank=True, null=True, help_text="Base URL of the review source")
    scraper_identifier = models.CharField(max_length=100, unique=True, blank=True, null=True, help_text="Identifier for the Apify scraper task/actor")

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']


class VeratourReport(models.Model):
    """
    Stores quantitative data from Veratour REPORT files.
    """
    resort = models.ForeignKey(Resort, on_delete=models.CASCADE, related_name='veratour_reports')
    total_guests = models.PositiveIntegerField(help_text="Totale persone / Ospiti (Schede Elaborate)")
    max_capacity = models.PositiveIntegerField(null=True, blank=True, help_text="Capienza Massima Struttura (inserita manualmente)")
    start_date = models.DateField()
    end_date = models.DateField()

    # Stores granular stats by department: { "RISTORAZIONE": {"positive": 95, "negative": 5, "sub_items": {...}}, ... }
    data = models.JSONField(default=dict, blank=True)

    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Report Veratour"
        verbose_name_plural = "Report Veratour"
        unique_together = ('resort', 'start_date', 'end_date')
        ordering = ['-start_date']

    def __str__(self):
        return f"Veratour Report {self.resort.name} ({self.start_date} - {self.end_date})"


class Review(models.Model):
    """
    Stores an individual review scraped from a source.
    """
    source = models.ForeignKey(ReviewSource, on_delete=models.CASCADE, related_name='reviews')
    resort = models.ForeignKey(Resort, on_delete=models.CASCADE, related_name='reviews')

    review_id = models.CharField(max_length=255, help_text="Unique ID of the review from the source platform")
    original_url = models.URLField(max_length=1024, blank=True, null=True, help_text="Direct link to the original review")
    author = models.CharField(max_length=255, blank=True)
    rating = models.FloatField(help_text="The rating given in the review (e.g., 4.5, 9.2)")
    title = models.CharField(max_length=255, blank=True)
    text = models.TextField(blank=True)

    review_date = models.DateTimeField(help_text="The original date and time the review was published")
    created_at = models.DateTimeField(auto_now_add=True, help_text="The date and time this review was saved into our system")

    def __str__(self):
        return f"Review by {self.author} for {self.resort.name} on {self.source.name}"

    class Meta:
        ordering = ['-review_date']
        unique_together = ('source', 'review_id') # Prevents saving the same review from the same source twice
        indexes = [
            models.Index(fields=['resort', 'review_date']),
            models.Index(fields=['rating']),
        ]


class ReviewAnalysis(models.Model):
    """
    Stores the results of sentiment analysis and other processing for a review.
    """
    SENTIMENT_CHOICES = [
        ('positive', 'Positive'),
        ('neutral', 'Neutral'),
        ('negative', 'Negative'),
    ]

    review = models.OneToOneField(Review, on_delete=models.CASCADE, related_name='analysis')

    sentiment_score = models.FloatField(help_text="Sentiment score from -1 (very negative) to 1 (very positive)")
    sentiment_label = models.CharField(max_length=10, choices=SENTIMENT_CHOICES, help_text="Categorical label for the sentiment")
    keywords = models.JSONField(default=list, blank=True, help_text="List of extracted keywords or topics")
    is_anomaly = models.BooleanField(default=False, help_text="True if the numeric rating is very high but the sentiment is very negative.")

    analyzed_at = models.DateTimeField(auto_now=True, help_text="When the analysis was last performed")

    def __str__(self):
        return f"Analysis for Review ID {self.review.id} ({self.get_sentiment_label_display()})"

    class Meta:
        ordering = ['-analyzed_at']


class ReportTemplate(models.Model):
    """
    Stores a user-defined configuration for generating a PDF report.
    """
    TYPE_SINGLE = 'single'
    TYPE_COMPARATIVE = 'comparative'
    REPORT_TYPE_CHOICES = [
        (TYPE_SINGLE, 'Analisi Singola'),
        (TYPE_COMPARATIVE, 'Analisi Comparativa'),
    ]

    name = models.CharField(max_length=255, verbose_name="Nome Template")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='report_templates')
    report_type = models.CharField(max_length=20, choices=REPORT_TYPE_CHOICES, default=TYPE_SINGLE)

    filters = models.JSONField(default=dict, help_text="Filtri di selezione per il report.")
    widgets = models.JSONField(default=list, help_text="Widget di contenuto da includere nel report.")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"'{self.name}' di {self.user.username}"

    class Meta:
        verbose_name = "Template di Report"
        verbose_name_plural = "Template di Report"
        ordering = ['user', '-updated_at']


class ScrapingURL(models.Model):
    resort = models.ForeignKey(Resort, on_delete=models.CASCADE, related_name='scraping_urls')
    source = models.ForeignKey(ReviewSource, on_delete=models.CASCADE, related_name='scraping_urls')
    url = models.URLField(max_length=1024, help_text="The specific URL for the resort on the review platform.")

    def __str__(self):
        return f"{self.resort.name} - {self.source.name}"

    class Meta:
        unique_together = ('resort', 'source')
        verbose_name = "URL da Scansionare"
        verbose_name_plural = "URL da Scansionare"


from django_celery_beat.models import PeriodicTask

class ScheduledScraping(models.Model):
    FREQUENCY_DAILY = 'daily'
    FREQUENCY_WEEKLY = 'weekly'
    FREQUENCY_CHOICES = [
        (FREQUENCY_DAILY, 'Ogni Giorno'),
        (FREQUENCY_WEEKLY, 'Ogni Settimana'),
    ]

    DAY_OF_WEEK_CHOICES = [
        ('1', 'Lunedì'), ('2', 'Martedì'), ('3', 'Mercoledì'),
        ('4', 'Giovedì'), ('5', 'Venerdì'), ('6', 'Sabato'), ('0', 'Domenica'),
    ]

    name = models.CharField(max_length=200, help_text="Un nome per questa attività di scraping, es. 'Scraping Giornaliero Google'")
    is_active = models.BooleanField(default=True, help_text="Disattiva per sospendere questa attività programmata.")

    # Scheduling fields
    frequency = models.CharField(max_length=10, choices=FREQUENCY_CHOICES, default=FREQUENCY_DAILY)
    day_of_week = models.CharField(max_length=1, choices=DAY_OF_WEEK_CHOICES, default='1', blank=True)
    hour = models.IntegerField(default=2)
    minute = models.IntegerField(default=0)

    # Scraping parameters
    resorts = models.ManyToManyField(Resort, blank=True, help_text="Seleziona i resort specifici. Se lasciato vuoto, li include tutti.")
    sources = models.ManyToManyField(ReviewSource, help_text="Seleziona le fonti da scansionare.")
    scrape_period_days = models.PositiveIntegerField(default=7, help_text="Recupera solo le recensioni degli ultimi X giorni. Lascia 0 per recuperarle tutte.")

    max_reviews_booking = models.PositiveIntegerField(default=50, help_text="Numero massimo di recensioni da recuperare da Booking.com.")
    max_reviews_google = models.PositiveIntegerField(default=50, help_text="Numero massimo di recensioni da recuperare da Google.")
    max_reviews_tripadvisor = models.PositiveIntegerField(default=50, help_text="Numero massimo di recensioni da recuperare da Tripadvisor.")

    # Celery task link
    periodic_task = models.OneToOneField(PeriodicTask, on_delete=models.SET_NULL, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Scraping Programmato"
        verbose_name_plural = "Scraping Programmati"
        ordering = ['name']

    def __str__(self):
        return self.name
