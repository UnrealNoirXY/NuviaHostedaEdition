from celery import shared_task
from django.utils import timezone
from accounts.models import User
from .nuvia_mail_sync_service import sync_read_only_inbox_for_user
from .nuvia_mail_service import process_send_queue_global
import logging

logger = logging.getLogger(__name__)

@shared_task(name='core.tasks.sync_all_mail_accounts')
def sync_all_mail_accounts():
    """Periodic task to sync all active mail accounts."""
    users = User.objects.filter(is_active=True, nuvia_mail_accounts__is_active=True).distinct()
    summary = {'users': 0, 'accounts': 0, 'folders': 0, 'messages': 0}

    for user in users:
        try:
            result = sync_read_only_inbox_for_user(user)
            summary['users'] += 1
            summary['accounts'] += result['accounts']
            summary['folders'] += result['folders']
            summary['messages'] += result['messages']
        except Exception as e:
            logger.error(f"Error syncing mail for user {user.username}: {str(e)}")

    return summary

@shared_task(name='core.tasks.process_mail_send_queue')
def process_mail_send_queue():
    """Periodic task to process pending mail in send queue."""
    return process_send_queue_global()
