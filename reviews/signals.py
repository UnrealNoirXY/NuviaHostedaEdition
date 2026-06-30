from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Review
from .services import analyze_review_sentiment

@receiver(post_save, sender=Review)
def review_saved_handler(sender, instance, created, **kwargs):
    """
    Signal handler that runs when a Review object is saved.

    If a new review is created, it triggers the sentiment analysis service.
    """
    if created:
        # We only want to run the analysis when a review is first created.
        # If you wanted to re-analyze on updates, you would remove this `if` condition.
        print(f"Signal received: New review (ID: {instance.id}) created. Triggering analysis.")
        analyze_review_sentiment(instance)
