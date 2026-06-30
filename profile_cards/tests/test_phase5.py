from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from profile_cards.models import ProfileCard, ProfileCardDelivery, ProfileCardEvent, ProfileCardPublicToken
from profile_cards.services import get_kpi_summary


class ProfileCardsPhase5Tests(TestCase):
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
            token="tok123",
            expires_at=timezone.now() + timedelta(days=3),
        )

    def test_public_profile_sets_noindex_and_tracks_open(self):
        url = reverse("profile_cards:public_profile", kwargs={"token": self.token.token})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["X-Robots-Tag"], "noindex, nofollow")
        self.token.refresh_from_db()
        self.assertEqual(self.token.open_count, 1)
        self.assertTrue(ProfileCardEvent.objects.filter(card=self.card, event_type=ProfileCardEvent.EVENT_OPEN).exists())

    def test_kpi_summary_counts_events_and_bounces(self):
        ProfileCardEvent.objects.create(card=self.card, token=self.token, event_type=ProfileCardEvent.EVENT_SHARE)
        ProfileCardDelivery.objects.create(card=self.card, recipient_email="a@example.com", status=ProfileCardDelivery.STATUS_BOUNCED)
        summary = get_kpi_summary(days=30)
        self.assertEqual(summary["shares"], 1)
        self.assertEqual(summary["email_bounces"], 1)

    def test_kpi_dashboard_superuser_only(self):
        User = get_user_model()
        user = User.objects.create_user(username="super", password="pwd", is_superuser=True)
        self.client.force_login(user)
        response = self.client.get(reverse("profile_cards:kpi_dashboard"))
        self.assertEqual(response.status_code, 200)
