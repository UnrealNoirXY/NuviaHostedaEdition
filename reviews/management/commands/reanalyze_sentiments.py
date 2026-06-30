from django.core.management.base import BaseCommand
from reviews.models import Review
from reviews.services import analyze_review_sentiment
from tqdm import tqdm

class Command(BaseCommand):
    help = 'Re-analyzes the sentiment for all existing reviews in the database.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting sentiment re-analysis for all reviews...'))

        reviews_to_analyze = Review.objects.all()

        for review in tqdm(reviews_to_analyze, desc="Analyzing Reviews"):
            try:
                analyze_review_sentiment(review)
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"Failed to analyze review {review.id}: {e}"))

        self.stdout.write(self.style.SUCCESS('Sentiment re-analysis complete.'))
