from datetime import timedelta
import io
from unittest.mock import patch
import zipfile

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from profile_cards.models import ProfileCard, ProfileCardEvent, ProfileCardPublicToken


class ProfileCardsPhase7Tests(TestCase):
    def setUp(self):
        self.card = ProfileCard.objects.create(
            first_name="Luca",
            last_name="Bianchi",
            role="Manager",
            email="luca@example.com",
            status=ProfileCard.STATUS_PUBLISHED,
        )
        self.token = ProfileCardPublicToken.objects.create(
            card=self.card,
            token="phase7tok",
            expires_at=timezone.now() + timedelta(days=5),
        )
        User = get_user_model()
        self.superuser = User.objects.create_user(
            username="superadmin_phase7",
            password="pwd",
            is_superuser=True,
        )

    def test_apple_pass_download_tracks_add_wallet(self):
        response = self.client.get(reverse("profile_cards:public_apple_pass", kwargs={"token": self.token.token}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/vnd.apple.pkpass")
        self.token.refresh_from_db()
        self.assertEqual(self.token.wallet_add_count, 1)
        self.assertTrue(ProfileCardEvent.objects.filter(event_type=ProfileCardEvent.EVENT_ADD_WALLET, source="wallet_apple").exists())

    def test_google_wallet_redirect_tracks_add_wallet(self):
        response = self.client.get(reverse("profile_cards:public_google_wallet", kwargs={"token": self.token.token}))
        self.assertEqual(response.status_code, 302)
        self.token.refresh_from_db()
        self.assertEqual(self.token.wallet_add_count, 1)
        self.assertTrue(ProfileCardEvent.objects.filter(event_type=ProfileCardEvent.EVENT_ADD_WALLET, source="wallet_google").exists())

    def test_admin_revoke_tokens_disables_token(self):
        self.client.force_login(self.superuser)
        response = self.client.post(reverse("profile_cards:admin_revoke_tokens", kwargs={"card_id": self.card.id}))
        self.assertEqual(response.status_code, 302)
        self.token.refresh_from_db()
        self.card.refresh_from_db()
        self.assertIsNotNone(self.token.revoked_at)
        self.assertEqual(self.card.status, ProfileCard.STATUS_REVOKED)

    def test_apple_pass_unsigned_contains_manifest_and_assets(self):
        response = self.client.get(reverse("profile_cards:public_apple_pass", kwargs={"token": self.token.token}))
        self.assertEqual(response.status_code, 200)

        with zipfile.ZipFile(io.BytesIO(response.content), "r") as zf:
            names = set(zf.namelist())
            self.assertIn("pass.json", names)
            self.assertIn("manifest.json", names)
            self.assertIn("icon.png", names)
            self.assertIn("icon@2x.png", names)
            self.assertIn("README.txt", names)
            self.assertNotIn("signature", names)

    @patch("profile_cards.wallet._sign_manifest", return_value=b"signed")
    @patch("profile_cards.wallet._has_signing_config", return_value=True)
    def test_apple_pass_signed_includes_signature(self, _has_signing_config_mock, _sign_manifest_mock):
        response = self.client.get(reverse("profile_cards:public_apple_pass", kwargs={"token": self.token.token}))
        self.assertEqual(response.status_code, 200)

        with zipfile.ZipFile(io.BytesIO(response.content), "r") as zf:
            names = set(zf.namelist())
            self.assertIn("signature", names)
            self.assertIn("manifest.json", names)
            self.assertNotIn("README.txt", names)



    @override_settings(PROFILE_CARDS_GOOGLE_WALLET_URL="")
    def test_google_wallet_uses_signed_google_save_url_when_configured(self):
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ).decode("utf-8")

        with self.settings(
            PROFILE_CARDS_GOOGLE_WALLET_CLIENT_EMAIL="wallet-sa@example.iam.gserviceaccount.com",
            PROFILE_CARDS_GOOGLE_WALLET_PRIVATE_KEY=private_pem,
            PROFILE_CARDS_GOOGLE_WALLET_ISSUER_ID="issuer123",
            PROFILE_CARDS_GOOGLE_WALLET_ISSUER_NAME="Noir Toolkit",
            PROFILE_CARDS_GOOGLE_WALLET_CLASS_SUFFIX="employee",
            BASE_URL="https://example.com",
        ):
            response = self.client.get(reverse("profile_cards:public_google_wallet", kwargs={"token": self.token.token}))

        self.assertEqual(response.status_code, 302)
        location = response["Location"]
        self.assertTrue(location.startswith("https://pay.google.com/gp/v/save/"))

    @override_settings(PROFILE_CARDS_GOOGLE_WALLET_URL="")
    def test_google_wallet_fallback_when_service_account_not_configured(self):
        response = self.client.get(reverse("profile_cards:public_google_wallet", kwargs={"token": self.token.token}))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], f"/cards/public/{self.token.token}/?wallet=google")

    @patch("profile_cards.views.send_profile_card_email")
    def test_admin_send_email_supports_multiple_recipients(self, send_mock):
        self.client.force_login(self.superuser)
        send_mock.return_value.status = "sent"
        response = self.client.post(
            reverse("profile_cards:admin_send_email", kwargs={"card_id": self.card.id}),
            {"recipient_email": "a@example.com, b@example.com"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(send_mock.call_count, 2)
