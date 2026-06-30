from django.core.management.base import BaseCommand
from competitors.services import trigger_competitor_scraping

class Command(BaseCommand):
    help = 'Fetches data for specified competitor scraping links.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--link-ids',
            nargs='+',
            type=int,
            help='A list of specific ScrapingLink IDs to run.',
        )

    def handle(self, *args, **options):
        link_ids = options.get('link_ids')

        if link_ids:
            self.stdout.write(self.style.SUCCESS(f"Starting scraping for specified link IDs: {link_ids}"))
            summary = trigger_competitor_scraping(scraping_link_ids=link_ids)
        else:
            self.stdout.write(self.style.SUCCESS("Starting scraping for all active competitor links..."))
            summary = trigger_competitor_scraping()

        self.stdout.write(self.style.SUCCESS("Scraping process finished."))
        if summary:
            self.stdout.write("Summary:")
            for key, value in summary.items():
                self.stdout.write(f"  - {key}: Saved {value.get('saved', 0)}, Skipped {value.get('skipped', 0)}, Error: {value.get('error', 'None')}")
        else:
            self.stdout.write("No links were processed.")
