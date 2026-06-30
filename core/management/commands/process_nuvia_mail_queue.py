from django.core.management.base import BaseCommand

from core.nuvia_mail_service import process_send_queue_global


class Command(BaseCommand):
    help = 'Processa la coda invio Nuvia Mail per tutti gli utenti attivi o per utenti specifici.'

    def add_arguments(self, parser):
        parser.add_argument('--limit-per-user', type=int, default=20)
        parser.add_argument('--user-id', type=int, action='append', dest='user_ids')

    def handle(self, *args, **options):
        result = process_send_queue_global(
            limit_per_user=options['limit_per_user'],
            user_ids=options.get('user_ids'),
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Processed users={result['users']} sent={result['sent']} failed={result['failed']} skipped={result['skipped']}"
            )
        )
