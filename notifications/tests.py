from datetime import timedelta

from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User
from clients.models import Company
from communications.models import Announcement
from desk.models import Event, EventInvitation
from notifications.models import Notification, PushSubscription
from notifications.push import (
    PushDeliveryError,
    WebPushException,
    enqueue_notification_push,
    send_push_notification,
)
from resort.models import Resort


class NotificationMatchingTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name='Test Company')
        self.resort = Resort.objects.create(name='Resort Uno', company=self.company)
        self.user = User.objects.create_user(
            username='alice',
            password='password',
            role=User.MAINTAINER,
            company=self.company,
            resort=self.resort,
        )

    def test_matches_user_with_role_and_scope(self):
        notification = Notification.objects.create(
            message='Avviso per manutentori',
            title='Nuova attività',
            category=Notification.Category.TASK,
            priority=Notification.Priority.NORMAL,
            audience_roles=[User.MAINTAINER],
            audience_company=self.company,
            audience_resort=self.resort,
        )

        self.assertTrue(notification.matches_user(self.user))

    def test_does_not_match_different_role(self):
        notification = Notification.objects.create(
            message='Solo direttori',
            audience_roles=[User.DIRECTOR],
        )

        self.assertFalse(notification.matches_user(self.user))

    def test_targeted_to_filters_out_other_roles(self):
        Notification.objects.create(
            message='Solo direttori',
            audience_roles=[User.DIRECTOR],
            audience_company=self.company,
            audience_resort=self.resort,
        )
        maintainer_notification = Notification.objects.create(
            message='Aggiornamento manutentori',
            audience_roles=[User.MAINTAINER],
            audience_company=self.company,
            audience_resort=self.resort,
        )

        targeted_ids = list(
            Notification.objects.targeted_to(self.user).values_list('id', flat=True)
        )

        self.assertIn(maintainer_notification.id, targeted_ids)
        self.assertEqual(len(targeted_ids), 1)


class NotificationFeedAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.company = Company.objects.create(name='Company Feed')
        self.resort = Resort.objects.create(name='Resort Feed', company=self.company)
        self.user = User.objects.create_user(
            username='feeduser',
            password='securepass',
            role=User.DIRECTOR,
            company=self.company,
            resort=self.resort,
        )
        self.client.force_login(self.user)

    def create_event_invitation(self):
        event = Event.objects.create(
            user=self.user,
            title='Riunione',
            start=timezone.now() + timedelta(hours=1),
            end=timezone.now() + timedelta(hours=2),
        )
        invitation = EventInvitation.objects.create(event=event, invitee=self.user)
        return invitation

    def test_feed_includes_notifications_announcements_and_invitations(self):
        Notification.objects.create(
            user=self.user,
            message='Ticket assegnato',
            title='Nuovo ticket',
            category=Notification.Category.TASK,
            priority=Notification.Priority.HIGH,
        )

        announcement = Announcement.objects.create(
            author=self.user,
            title='Aggiornamento importate',
            body='Nuove procedure disponibili.',
        )
        announcement.recipients.add(self.user)

        invitation = self.create_event_invitation()

        response = self.client.get(reverse('notifications_api:feed'))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        types = {item['type'] for item in payload['results']}
        self.assertIn('in_app', types)
        self.assertIn('announcement', types)
        self.assertIn('event_invitation', types)
        self.assertGreaterEqual(payload['unread_count'], 3)

        invitation_ids = [item['metadata']['invitation_id'] for item in payload['results'] if item['type'] == 'event_invitation']
        self.assertIn(invitation.id, invitation_ids)

    def test_mark_notification_read_updates_counter(self):
        notification = Notification.objects.create(
            user=self.user,
            message='Nuovo messaggio',
            title='Notifica',
        )
        Announcement.objects.create(
            author=self.user,
            title='Memo',
            body='Ricordati di completare il report.',
        ).recipients.add(self.user)

        url = reverse('notifications_api:mark_read', args=[notification.id])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        # Should include announcements in the counter
        self.assertGreaterEqual(data['unread_count'], 1)


class PushDeliveryTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name='Push Company')
        self.resort = Resort.objects.create(name='Push Resort', company=self.company)
        self.user = User.objects.create_user(
            username='pushuser',
            password='password',
            email='push@example.com',
            role=User.DIRECTOR,
            company=self.company,
            resort=self.resort,
        )
        self.subscription = PushSubscription.objects.create(
            user=self.user,
            endpoint='https://push.example.com/subscription/1',
            p256dh='p256dh-key',
            auth='auth-key',
            device_type=PushSubscription.DEVICE_WEB,
        )

    @override_settings(
        WEB_PUSH_VAPID_PUBLIC_KEY='test-public',
        WEB_PUSH_VAPID_PRIVATE_KEY='test-private',
        WEB_PUSH_CONTACT_EMAIL='mailto:test@example.com',
        CELERY_TASK_ALWAYS_EAGER=True,
        CELERY_TASK_EAGER_PROPAGATES=True,
    )
    @patch('notifications.push.webpush')
    def test_enqueue_notification_push_executes_task(self, mock_webpush):
        payload = {'title': 'Titolo', 'body': 'Messaggio'}

        enqueue_notification_push(self.subscription, payload, reason='unit_test')

        mock_webpush.assert_called_once()

    @override_settings(
        WEB_PUSH_VAPID_PUBLIC_KEY='test-public',
        WEB_PUSH_VAPID_PRIVATE_KEY='test-private',
        WEB_PUSH_CONTACT_EMAIL='mailto:test@example.com',
    )
    @patch('notifications.push.webpush')
    def test_send_push_notification_deactivates_subscription_on_gone(self, mock_webpush):
        class FakeResponse:
            status_code = 410

        class FakeWebPushException(WebPushException):
            def __init__(self, message):
                super().__init__(message)
                self.response = FakeResponse()

        mock_webpush.side_effect = FakeWebPushException('gone')

        with self.assertRaises(PushDeliveryError):
            send_push_notification(self.subscription, {'title': 'Errore', 'body': 'Test'})

        self.subscription.refresh_from_db()
        self.assertFalse(self.subscription.is_active)


class NotificationPushSignalTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name='Signal Company')
        self.other_company = Company.objects.create(name='Other Company')
        self.resort = Resort.objects.create(name='Signal Resort', company=self.company)
        self.user = User.objects.create_user(
            username='signaluser',
            password='password',
            role=User.DIRECTOR,
            company=self.company,
            resort=self.resort,
        )
        self.other_user = User.objects.create_user(
            username='otheruser',
            password='password',
            role=User.MAINTAINER,
            company=self.other_company,
        )
        self.subscription = PushSubscription.objects.create(
            user=self.user,
            endpoint='https://push.example.com/subscription/signal',
            p256dh='signal-p256dh',
            auth='signal-auth',
            device_type=PushSubscription.DEVICE_WEB,
        )
        self.other_subscription = PushSubscription.objects.create(
            user=self.other_user,
            endpoint='https://push.example.com/subscription/other',
            p256dh='other-p256dh',
            auth='other-auth',
            device_type=PushSubscription.DEVICE_WEB,
        )

    @patch('notifications.signals.enqueue_notification_push')
    def test_direct_notification_triggers_push(self, mock_enqueue):
        Notification.objects.create(
            user=self.user,
            message='Aggiornamento ticket',
            link='/tickets/1/',
            delivery_channels=['in_app', 'push'],
        )

        mock_enqueue.assert_called_once()
        subscription, payload = mock_enqueue.call_args[0][:2]
        self.assertEqual(subscription, self.subscription)
        self.assertEqual(payload['title'], 'Aggiornamento ticket')
        self.assertEqual(payload['url'], '/tickets/1/')

    @patch('notifications.signals.enqueue_notification_push')
    def test_notification_without_push_channel_skips_delivery(self, mock_enqueue):
        Notification.objects.create(
            user=self.user,
            message='Solo in app',
            delivery_channels=['in_app'],
        )

        mock_enqueue.assert_not_called()

    @patch('notifications.signals.enqueue_notification_push')
    def test_broadcast_notification_filters_subscriptions(self, mock_enqueue):
        Notification.objects.create(
            message='Aggiornamento manutentori',
            audience_company=self.company,
            audience_roles=[User.DIRECTOR],
            delivery_channels=['in_app', 'push'],
        )

        mock_enqueue.assert_called_once()
        targeted_subscription = mock_enqueue.call_args[0][0]
        self.assertEqual(targeted_subscription, self.subscription)
