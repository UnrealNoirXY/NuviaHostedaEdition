from datetime import timedelta
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from profile_cards.emailing import send_profile_card_email
from profile_cards.models import ProfileCard, ProfileCardDelivery, ProfileCardEvent, ProfileCardPublicToken


class ProfileCardsPhase6Tests(TestCase):
    def setUp(self):
        self.card = ProfileCard.objects.create(
            first_name="Mario",
            last_name="Rossi",
            role="Sales",
            email="mario@example.com",
            status=ProfileCard.STATUS_PUBLISHED,
        )
        self.token = ProfileCardPublicToken.objects.create(
            card=self.card,
            token="tok456",
            expires_at=timezone.now() + timedelta(days=3),
        )

    def test_public_vcard_download_tracks_event(self):
        response = self.client.get(reverse("profile_cards:public_vcard", kwargs={"token": self.token.token}))
        self.assertEqual(response.status_code, 200)
        self.assertIn("BEGIN:VCARD", response.content.decode("utf-8"))
        self.token.refresh_from_db()
        self.assertEqual(self.token.vcard_download_count, 1)
        self.assertTrue(ProfileCardEvent.objects.filter(event_type=ProfileCardEvent.EVENT_VCARD).exists())

    def test_admin_dashboard_requires_superadmin(self):
        User = get_user_model()
        user = User.objects.create_user(username="normal", password="pwd", role="owner")
        self.client.force_login(user)
        response = self.client.get(reverse("profile_cards:admin_dashboard"))
        self.assertEqual(response.status_code, 403)

    @patch("profile_cards.emailing.get_connection")
    def test_send_profile_card_email_uses_default_otp_channel(self, get_connection_mock):
        connection = Mock()
        get_connection_mock.return_value = connection
        with patch("profile_cards.emailing.EmailMultiAlternatives.send", return_value=1):
            send_profile_card_email(
                card=self.card,
                public_url="https://example.com/cards/public/tok456/",
                recipient_email="cliente@example.com",
            )

        kwargs = get_connection_mock.call_args.kwargs
        self.assertIn("host", kwargs)
        self.assertIn("port", kwargs)
        delivery = ProfileCardDelivery.objects.get(recipient_email="cliente@example.com")
        self.assertEqual(delivery.status, ProfileCardDelivery.STATUS_SENT)
