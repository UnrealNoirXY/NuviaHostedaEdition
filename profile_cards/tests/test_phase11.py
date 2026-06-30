from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from profile_cards.models import ProfileCard, ProfileCardDelivery, ProfileCardEvent, ProfileCardPublicToken
from profile_cards.services import get_kpi_summary


class ProfileCardsPhase11Tests(TestCase):
    def test_phase11_rates_are_computed(self):
        card = ProfileCard.objects.create(
            first_name="Anna",
            last_name="Verdi",
            role="Marketing",
            email="anna@example.com",
            status=ProfileCard.STATUS_PUBLISHED,
        )
        token = ProfileCardPublicToken.objects.create(
            card=card,
            token="kpi11",
            expires_at=timezone.now() + timedelta(days=2),
        )

        ProfileCardEvent.objects.create(card=card, token=token, event_type=ProfileCardEvent.EVENT_OPEN)
        ProfileCardEvent.objects.create(card=card, token=token, event_type=ProfileCardEvent.EVENT_SHARE)
        ProfileCardEvent.objects.create(card=card, token=token, event_type=ProfileCardEvent.EVENT_VCARD)
        ProfileCardEvent.objects.create(card=card, token=token, event_type=ProfileCardEvent.EVENT_ADD_WALLET)
        ProfileCardDelivery.objects.create(card=card, recipient_email="ok@example.com", status=ProfileCardDelivery.STATUS_SENT)
        ProfileCardDelivery.objects.create(card=card, recipient_email="ko@example.com", status=ProfileCardDelivery.STATUS_BOUNCED)

        summary = get_kpi_summary(days=30)
        self.assertEqual(summary["open_rate"], 100.0)
        self.assertEqual(summary["share_rate"], 100.0)
        self.assertEqual(summary["vcard_rate"], 100.0)
        self.assertEqual(summary["wallet_add_rate"], 100.0)
        self.assertEqual(summary["email_success_rate"], 50.0)
        self.assertGreaterEqual(summary["avg_card_creation_per_day"], 0)
