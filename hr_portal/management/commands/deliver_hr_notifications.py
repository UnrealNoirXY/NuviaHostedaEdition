from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from hr_portal.models import HRNotification
from hr_portal.services import deliver_notification


class Command(BaseCommand):
    help = "Deliver scheduled HR notifications respecting audience and channel preferences"

    def handle(self, *args, **options):
        now = timezone.now()
        qs = HRNotification.objects.filter(status=HRNotification.STATUS_PUBLISHED)
        qs = qs.filter((Q(scheduled_for__isnull=True) | Q(scheduled_for__lte=now)))
        qs = qs.filter((Q(expires_at__isnull=True) | Q(expires_at__gt=now)))

        for notification in qs:
            result = deliver_notification(notification)
            self.stdout.write(
                self.style.SUCCESS(
                    f"Notifica {notification.id}: {len(result.deliveries)} consegne, errori: {len(result.errors)}"
                )
            )
