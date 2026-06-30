from django.core.management.base import BaseCommand
from reviews.services import trigger_review_scraping

class Command(BaseCommand):
    help = 'Fetches reviews from Apify for all configured sources and URLs.'

    def handle(self, *args, **options):
        self.stdout.write("Starting review scraping process for all resorts...")

        try:
            summary = trigger_review_scraping()
            self.stdout.write(self.style.SUCCESS("Scraping process finished."))

            for source_name, results in summary.items():
                if 'error' in results:
                    self.stderr.write(self.style.ERROR(f"Source '{source_name}': FAILED with error: {results['error']}"))
                else:
                    self.stdout.write(f"Source '{source_name}': Saved {results.get('saved', 0)} new reviews, skipped {results.get('skipped', 0)}.")

        except Exception as e:
            self.stderr.write(self.style.ERROR(f"An unexpected error occurred during the scraping process: {e}"))

