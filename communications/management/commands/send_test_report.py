import os
from django.core.management.base import BaseCommand, CommandError
from communications.models import ScheduledEmailReport
from communications.tasks import send_review_report

class Command(BaseCommand):
    help = 'Sends a test email for a scheduled report'

    def add_arguments(self, parser):
        parser.add_argument('report_id', type=int, help='The ID of the scheduled report to test')

    def handle(self, *args, **options):
        # Set a dummy secret key if not present
        if 'SECRET_KEY' not in os.environ:
            os.environ['SECRET_KEY'] = 'dummy-secret-key-for-testing'

        report_id = options['report_id']
        try:
            report = ScheduledEmailReport.objects.get(pk=report_id)
            self.stdout.write(f"Found report: {report.name}")
        except ScheduledEmailReport.DoesNotExist:
            raise CommandError(f'ScheduledEmailReport with id "{report_id}" does not exist.')

        self.stdout.write("Calling send_review_report task...")

        # We call the task directly to see the output
        # In a real scenario, you might use .delay() or .apply_async()
        result = send_review_report(report.id)

        self.stdout.write(self.style.SUCCESS('Task executed.'))
        self.stdout.write(f"Result: {result}")
