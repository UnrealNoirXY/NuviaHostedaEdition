from django.utils import timezone
from notifications.models import Notification

from .models import (
    NuviaMailAccount,
    NuviaMailFolder,
    NuviaMailMessage,
    NuviaMailSyncCheckpoint,
    NuviaMailThread,
)
from .nuvia_mail_providers import NuviaMailProviderError, get_provider_adapter


def sync_read_only_inbox_for_account(account: NuviaMailAccount):
    adapter = get_provider_adapter(account)
    folders_data = adapter.list_folders()

    synced_folders = 0
    synced_messages = 0

    for folder_data in folders_data:
        folder, _ = NuviaMailFolder.objects.get_or_create(
            account=account,
            provider_folder_id=folder_data['id'],
            defaults={
                'user': account.user,
                'name': folder_data['name'],
                'is_inbox': bool(folder_data.get('is_inbox')),
                'is_sent': bool(folder_data.get('is_sent')),
            },
        )
        if folder.name != folder_data['name']:
            folder.name = folder_data['name']
            folder.is_inbox = bool(folder_data.get('is_inbox'))
            folder.is_sent = bool(folder_data.get('is_sent'))
            folder.save(update_fields=['name', 'is_inbox', 'is_sent', 'updated_at'])

        checkpoint, _ = NuviaMailSyncCheckpoint.objects.get_or_create(
            user=account.user,
            account=account,
            folder=folder,
        )

        try:
            delta = adapter.list_messages_delta(cursor=checkpoint.cursor or None, folder_id=folder.provider_folder_id)
            messages = delta.get('messages', [])
            for msg in messages:
                thread, _ = NuviaMailThread.objects.get_or_create(
                    user=account.user,
                    account=account,
                    folder=folder,
                    provider_thread_id=msg.get('provider_thread_id', ''),
                    defaults={
                        'subject': msg.get('subject', ''),
                        'last_message_at': msg.get('received_at') or timezone.now(),
                    },
                )
                message_obj, created = NuviaMailMessage.objects.update_or_create(
                    user=account.user,
                    account=account,
                    folder=folder,
                    thread=thread,
                    provider_message_id=msg['provider_message_id'],
                    defaults={
                        'subject': msg.get('subject', ''),
                        'from_email': msg.get('from_email', ''),
                        'to_emails': msg.get('to_emails', ''),
                        'body_text': msg.get('body_text', ''),
                        'body_html': msg.get('body_html', ''),
                        'message_id_header': msg.get('message_id_header', ''),
                        'in_reply_to': msg.get('in_reply_to', ''),
                        'references_header': msg.get('references_header', ''),
                        'received_at': msg.get('received_at') or timezone.now(),
                    },
                )
                if created and folder.is_inbox:
                    Notification.objects.create(
                        user=account.user,
                        title=f"Nuova email da {msg.get('from_email', 'Sconosciuto')}",
                        message=msg.get('subject', '(Senza oggetto)'),
                        category=Notification.Category.GENERAL,
                        priority=Notification.Priority.NORMAL,
                        icon="fa-envelope",
                        link=f"/nuvia-mail/?thread={thread.id}",
                        source="nuvia_mail"
                    )
                thread.subject = msg.get('subject', thread.subject)
                thread.last_message_at = msg.get('received_at') or timezone.now()
                thread.save(update_fields=['subject', 'last_message_at', 'updated_at'])
                synced_messages += 1

            checkpoint.cursor = delta.get('next_cursor', checkpoint.cursor)
            checkpoint.last_error = ''
            checkpoint.last_synced_at = timezone.now()
            checkpoint.save(update_fields=['cursor', 'last_error', 'last_synced_at', 'updated_at'])
        except NuviaMailProviderError as exc:
            checkpoint.last_error = str(exc)[:255]
            checkpoint.save(update_fields=['last_error', 'updated_at'])

        synced_folders += 1

    return {'folders': synced_folders, 'messages': synced_messages}


def sync_read_only_inbox_for_user(user):
    total = {'accounts': 0, 'folders': 0, 'messages': 0}
    accounts = NuviaMailAccount.objects.filter(user=user, is_active=True)
    for account in accounts.iterator():
        result = sync_read_only_inbox_for_account(account)
        total['accounts'] += 1
        total['folders'] += result['folders']
        total['messages'] += result['messages']
    return total
