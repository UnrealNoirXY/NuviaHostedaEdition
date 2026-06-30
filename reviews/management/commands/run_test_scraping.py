import os
from django.core.management.base import BaseCommand, CommandError
from reviews.models import ScheduledScraping
from reviews.tasks import run_scheduled_scraping

class Command(BaseCommand):
    help = 'Triggers a scheduled scraping task for testing purposes'

    def add_arguments(self, parser):
        parser.add_argument('scraping_id', type=int, help='The ID of the scheduled scraping task to run')

    def handle(self, *args, **options):
        if 'SECRET_KEY' not in os.environ:
            os.environ['SECRET_KEY'] = 'dummy-secret-key-for-testing'

        scraping_id = options['scraping_id']
        try:
            job = ScheduledScraping.objects.get(pk=scraping_id)
            self.stdout.write(f"Found scheduled scraping job: {job.name}")
        except ScheduledScraping.DoesNotExist:
            raise CommandError(f'ScheduledScraping with id "{scraping_id}" does not exist.')

        self.stdout.write("Calling run_scheduled_scraping task directly...")

        result = run_scheduled_scraping(job.id)

        self.stdout.write(self.style.SUCCESS('Task executed.'))
        self.stdout.write(f"Result: {result}")
