from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import ScrapedData
from .services import analyze_competitor_data

@receiver(post_save, sender=ScrapedData)
def run_analysis_on_new_data(sender, instance, created, **kwargs):
    """
    When a new piece of scraped data is saved, trigger sentiment analysis.
    """
    if created:
        # We run this in a simple way for now.
        # For a production system, this should be offloaded to a Celery task
        # to avoid blocking the request-response cycle if the analysis is slow.
        try:
            analyze_competitor_data(instance)
        except Exception as e:
            # Log the error but don't crash the save operation
            print(f"Error triggering analysis for ScrapedData {instance.id}: {e}")
