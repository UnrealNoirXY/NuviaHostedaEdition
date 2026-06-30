from django.db.models import Q
from django.utils import timezone

from accounts.models import User

from .models import NuviaMailSendQueue
from .nuvia_mail_providers import NuviaMailProviderError, get_provider_adapter


def process_send_queue_for_user(user, *, limit=20):
    now = timezone.now()
    queryset = NuviaMailSendQueue.objects.filter(
        user=user,
        status=NuviaMailSendQueue.STATUS_QUEUED,
        compliance_flagged=False,
    ).filter(Q(scheduled_for__isnull=True) | Q(scheduled_for__lte=now)).order_by('created_at')

    sent = 0
    failed = 0
    skipped = 0

    for item in queryset[:limit]:
        item.last_attempt_at = now
        try:
            adapter = get_provider_adapter(item.account)
            send_result = adapter.send_message(
                to_email=item.to_email,
                subject=item.subject,
                body=item.body,
            )
            item.status = NuviaMailSendQueue.STATUS_SENT
            item.sent_at = now
            item.error_message = ''
            item.provider_message_id = send_result.provider_message_id
            item.save(update_fields=['status', 'sent_at', 'error_message', 'provider_message_id', 'last_attempt_at'])
            sent += 1
        except (NuviaMailProviderError, Exception) as exc:  # pragma: no cover
            item.retry_count += 1
            item.error_message = str(exc)[:255]
            if item.retry_count >= item.max_retries:
                item.status = NuviaMailSendQueue.STATUS_FAILED
                failed += 1
            else:
                skipped += 1
            item.save(update_fields=['retry_count', 'error_message', 'status', 'last_attempt_at'])

    return {'sent': sent, 'failed': failed, 'skipped': skipped}


def process_send_queue_global(*, limit_per_user=20, user_ids=None):
    users = User.objects.filter(is_active=True)
    if user_ids:
        users = users.filter(pk__in=user_ids)

    summary = {'users': 0, 'sent': 0, 'failed': 0, 'skipped': 0}
    for user in users.iterator():
        result = process_send_queue_for_user(user, limit=limit_per_user)
        if result['sent'] or result['failed'] or result['skipped']:
            summary['users'] += 1
        summary['sent'] += result['sent']
        summary['failed'] += result['failed']
        summary['skipped'] += result['skipped']
    return summary
