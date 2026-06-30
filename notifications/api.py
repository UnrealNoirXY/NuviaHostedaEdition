from django.conf import settings
from django.urls import reverse
from django.utils import dateparse, timezone
from rest_framework import permissions, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from communications.models import Announcement
from desk.models import EventInvitation
from .models import Notification, PushSubscription
from .push import PushDeliveryError, enqueue_notification_push


class NotificationSerializer(serializers.ModelSerializer):
    title = serializers.SerializerMethodField()
    body = serializers.SerializerMethodField()
    cta_url = serializers.CharField(source="link")

    class Meta:
        model = Notification
        fields = [
            "id",
            "title",
            "message",
            "body",
            "category",
            "priority",
            "icon",
            "cta_label",
            "cta_url",
            "is_read",
            "is_pinned",
            "requires_acknowledgement",
            "metadata",
            "created_at",
            "read_at",
            "source",
        ]

    def get_title(self, obj: Notification) -> str:
        return obj.display_title

    def get_body(self, obj: Notification) -> str:
        return obj.body or obj.message


def _visible_announcements_for(user: User):
    """Return announcements that should be visible to the user."""

    return (
        Announcement.objects.filter(recipients=user)
        .exclude(read_by=user)
        .order_by("-created_at")
        .distinct()
    )


class NotificationFeedView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    DEFAULT_LIMIT = 20
    MAX_LIMIT = 100

    def get(self, request, *args, **kwargs):
        user: User = request.user
        limit = self._get_limit(request)
        cursor = request.query_params.get("cursor")

        queryset = Notification.objects.targeted_to(user).order_by("-is_pinned", "-created_at")

        if cursor:
            parsed_cursor = dateparse.parse_datetime(cursor)
            if parsed_cursor is not None:
                parsed_cursor = parsed_cursor.astimezone(timezone.utc)
                queryset = queryset.filter(created_at__lt=parsed_cursor)

        collected = []
        batch_size = limit * 3

        for notification in queryset[: batch_size + 1]:
            if notification.matches_user(user):
                collected.append(notification)

        announcement_items = [
            {
                "id": f"announcement-{ann.id}",
                "title": ann.title,
                "message": ann.title,
                "body": ann.body,
                "category": "system",
                "priority": Notification.Priority.LOW,
                "icon": "fa-bullhorn",
                "cta_label": "Apri",
                "cta_url": reverse('communications:detail', args=[ann.id]),
                "is_read": False,
                "is_pinned": False,
                "requires_acknowledgement": False,
                "metadata": {"announcement_id": ann.id},
                "created_at": ann.created_at.isoformat(),
                "read_at": None,
                "source": "communications",
                "type": "announcement",
            }
            for ann in _visible_announcements_for(user)[:5]
        ]

        invitation_items = []
        invitations = EventInvitation.objects.filter(invitee=user, status="pending").select_related("event", "event__user")
        for invitation in invitations:
            invitation_items.append(
                {
                    "id": f"invitation-{invitation.id}",
                    "title": f"Invito a: {invitation.event.title}",
                    "message": f"{invitation.event.user.get_full_name() or invitation.event.user.username}",
                    "body": "",
                    "category": "general",
                    "priority": Notification.Priority.NORMAL,
                    "icon": "fa-calendar-plus",
                    "cta_label": "Apri",
                    "cta_url": reverse('desk:home'),
                    "is_read": False,
                    "is_pinned": True,
                    "requires_acknowledgement": True,
                    "metadata": {
                        "invitation_id": invitation.id,
                        "invitation_api": reverse('desk_api:update_invitation_status', args=[invitation.id]),
                    },
                    "created_at": invitation.event.start.isoformat(),
                    "read_at": None,
                    "source": "calendar",
                    "type": "event_invitation",
                }
            )

        serialized_notifications = NotificationSerializer(collected, many=True).data
        normalized_notifications = [
            {**item, "type": "in_app"} for item in serialized_notifications
        ]

        combined_items = normalized_notifications + announcement_items + invitation_items
        combined_items.sort(key=lambda item: item["created_at"], reverse=True)

        results = combined_items[:limit]
        has_more = len(combined_items) > limit
        if results:
            last_created = results[-1]["created_at"]
            next_cursor = last_created if isinstance(last_created, str) else last_created.isoformat()
        else:
            next_cursor = None

        unread_count = self._compute_unread_count(user) + len(announcement_items) + len(invitation_items)

        return Response(
            {
                "results": results,
                "unread_count": unread_count,
                "next_cursor": next_cursor,
                "has_more": has_more,
            }
        )

    def _get_limit(self, request):
        try:
            limit = int(request.query_params.get("limit", self.DEFAULT_LIMIT))
        except (TypeError, ValueError):
            return self.DEFAULT_LIMIT

        return max(1, min(limit, self.MAX_LIMIT))

    def _compute_unread_count(self, user):
        unread_qs = Notification.objects.unread_for(user)
        count = 0
        for notification in unread_qs.iterator():
            if notification.matches_user(user):
                count += 1
        return count


class NotificationSummaryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        base_unread = NotificationFeedView()._compute_unread_count(request.user)
        announcement_count = _visible_announcements_for(request.user).count()
        invitation_count = EventInvitation.objects.filter(invitee=request.user, status="pending").count()

        most_recent_notification = (
            Notification.objects.targeted_to(request.user)
            .order_by("-created_at")
            .first()
        )
        latest_dates = []
        if most_recent_notification:
            latest_dates.append(most_recent_notification.created_at)
        latest_announcement = _visible_announcements_for(request.user).values_list("created_at", flat=True).first()
        if latest_announcement:
            latest_dates.append(latest_announcement)
        latest_invitation = (
            EventInvitation.objects.filter(invitee=request.user)
            .order_by("-event__start")
            .values_list("event__start", flat=True)
            .first()
        )
        if latest_invitation:
            latest_dates.append(latest_invitation)

        latest_created_at = max(latest_dates).isoformat() if latest_dates else None

        return Response(
            {
                "unread_count": base_unread + announcement_count + invitation_count,
                "latest_created_at": latest_created_at,
            }
        )


class MarkNotificationReadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, notification_id, *args, **kwargs):
        notification = Notification.objects.filter(pk=notification_id).first()
        if not notification or not notification.matches_user(request.user):
            return Response(status=status.HTTP_404_NOT_FOUND)

        notification.mark_as_read(save=True)
        base_unread = NotificationFeedView()._compute_unread_count(request.user)
        announcement_count = _visible_announcements_for(request.user).count()
        invitation_count = EventInvitation.objects.filter(invitee=request.user, status="pending").count()
        unread_count = base_unread + announcement_count + invitation_count

        return Response({"status": "ok", "unread_count": unread_count})


class MarkAllNotificationsReadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        notifications = Notification.objects.unread_for(request.user)
        now = timezone.now()
        updated = 0
        for notification in notifications:
            if notification.matches_user(request.user):
                notification.mark_as_read(timestamp=now, save=True)
                updated += 1

        for announcement in _visible_announcements_for(request.user):
            announcement.read_by.add(request.user)

        return Response({"status": "ok", "updated": updated})


class PushSubscriptionSerializer(serializers.Serializer):
    endpoint = serializers.URLField()
    keys = serializers.DictField(child=serializers.CharField(), allow_empty=False)
    device_type = serializers.ChoiceField(choices=PushSubscription.DEVICE_CHOICES, default=PushSubscription.DEVICE_WEB)


class PushSubscriptionView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = PushSubscriptionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        endpoint = data["endpoint"]
        keys = data["keys"]
        device_type = data.get("device_type", PushSubscription.DEVICE_WEB)

        subscription, _ = PushSubscription.objects.update_or_create(
            endpoint=endpoint,
            defaults={
                "user": request.user,
                "p256dh": keys.get("p256dh", ""),
                "auth": keys.get("auth", ""),
                "device_type": device_type,
                "user_agent": request.META.get("HTTP_USER_AGENT", ""),
                "is_active": True,
            },
        )

        return Response({"id": str(subscription.id), "status": "registered"}, status=status.HTTP_201_CREATED)

    def delete(self, request, *args, **kwargs):
        endpoint = request.data.get("endpoint")
        if not endpoint:
            return Response({"detail": "Missing endpoint"}, status=status.HTTP_400_BAD_REQUEST)

        subscription = PushSubscription.objects.filter(endpoint=endpoint, user=request.user).first()
        if not subscription:
            return Response(status=status.HTTP_204_NO_CONTENT)

        subscription.is_active = False
        subscription.save(update_fields=["is_active", "updated_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class SendTestPushView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        if settings.DEBUG is False and not request.user.is_staff:
            return Response(status=status.HTTP_403_FORBIDDEN)

        subscription_id = request.data.get("subscription_id")
        if not subscription_id:
            return Response({"detail": "subscription_id richiesto"}, status=status.HTTP_400_BAD_REQUEST)

        subscription = PushSubscription.objects.filter(id=subscription_id, user=request.user, is_active=True).first()
        if not subscription:
            return Response({"detail": "Subscription non trovata"}, status=status.HTTP_404_NOT_FOUND)

        payload = {
            "title": "Test Push",
            "body": "Le notifiche push sono correttamente configurate.",
            "category": "system",
            "priority": "normal",
        }

        try:
            enqueue_notification_push(subscription, payload, reason="manual_test_push")
        except PushDeliveryError as exc:  # pragma: no cover - safety guard
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"status": "queued"})

