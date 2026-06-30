from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from profile_cards.models import CardTemplate, ProfileCard, ProfileCardSettings
from profile_cards.tokens import issue_public_token


class ProfileCardsPhase14Tests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.superuser = User.objects.create_user(
            username="phase14admin",
            password="pwd",
            is_superuser=True,
        )

    def test_issue_public_token_uses_settings_default_days(self):
        settings_obj = ProfileCardSettings.get_solo()
        settings_obj.default_token_days = 30
        settings_obj.save(update_fields=["default_token_days"])

        card = ProfileCard.objects.create(
            first_name="Giulia",
            last_name="Neri",
            role="HR",
            email="giulia@example.com",
            status=ProfileCard.STATUS_PUBLISHED,
        )
        token = issue_public_token(card)
        delta_days = (token.expires_at - timezone.now()).days
        self.assertGreaterEqual(delta_days, 29)

    def test_admin_settings_enforce_required_phone(self):
        self.client.force_login(self.superuser)
        settings_obj = ProfileCardSettings.get_solo()
        settings_obj.require_phone = True
        settings_obj.save(update_fields=["require_phone"])

        response = self.client.post(
            reverse("profile_cards:admin_dashboard"),
            {
                "first_name": "Lara",
                "last_name": "Blu",
                "role": "Ops",
                "email": "lara@example.com",
                "phone": "",
                "department": "Operations",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(ProfileCard.objects.filter(email="lara@example.com").exists())

    def test_admin_create_card_with_template(self):
        self.client.force_login(self.superuser)
        template = CardTemplate.objects.create(name="Corporate", company_name="Noir")

        response = self.client.post(
            reverse("profile_cards:admin_dashboard"),
            {
                "first_name": "Marta",
                "last_name": "Rosa",
                "role": "Sales",
                "email": "marta@example.com",
                "phone": "+390000",
                "department": "Sales",
                "template_id": str(template.id),
            },
        )
        self.assertEqual(response.status_code, 302)
        card = ProfileCard.objects.get(email="marta@example.com")
        self.assertEqual(card.template, template)
