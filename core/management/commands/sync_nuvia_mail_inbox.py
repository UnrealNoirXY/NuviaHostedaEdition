from django.core.management.base import BaseCommand

from accounts.models import User
from core.nuvia_mail_sync_service import sync_read_only_inbox_for_user


class Command(BaseCommand):
    help = 'Esegue sync read-only inbox Nuvia Mail per utenti attivi o selezionati.'

    def add_arguments(self, parser):
        parser.add_argument('--user-id', type=int, action='append', dest='user_ids')

    def handle(self, *args, **options):
        users = User.objects.filter(is_active=True)
        user_ids = options.get('user_ids')
        if user_ids:
            users = users.filter(pk__in=user_ids)

        summary = {'users': 0, 'accounts': 0, 'folders': 0, 'messages': 0}
        for user in users.iterator():
            result = sync_read_only_inbox_for_user(user)
            if result['accounts']:
                summary['users'] += 1
            summary['accounts'] += result['accounts']
            summary['folders'] += result['folders']
            summary['messages'] += result['messages']

        self.stdout.write(
            self.style.SUCCESS(
                f"Synced users={summary['users']} accounts={summary['accounts']} folders={summary['folders']} messages={summary['messages']}"
            )
        )
