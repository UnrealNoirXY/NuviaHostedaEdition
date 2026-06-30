from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from profile_cards.models import CardTemplate, ProfileCard, ProfileCardSettings


class ProfileCardsPhase15Tests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.superuser = User.objects.create_user(username="phase15admin", password="pwd", is_superuser=True)

    def test_create_card_uses_default_template_version(self):
        template = CardTemplate.objects.create(name="Default Brand", company_name="Noir", is_default=True, version=3)
        self.client.force_login(self.superuser)
        response = self.client.post(
            reverse("profile_cards:admin_dashboard"),
            {
                "first_name": "Pietro",
                "last_name": "Bello",
                "role": "Consultant",
                "email": "pietro@example.com",
                "phone": "",
                "department": "",
                "template_id": "",
            },
        )
        self.assertEqual(response.status_code, 302)
        card = ProfileCard.objects.get(email="pietro@example.com")
        self.assertEqual(card.template, template)
        self.assertEqual(card.applied_template_version, 3)

    def test_bump_template_version_updates_cards_when_auto_update_enabled(self):
        template = CardTemplate.objects.create(name="Brand X", is_default=True, version=1)
        card = ProfileCard.objects.create(
            template=template,
            applied_template_version=1,
            first_name="A",
            last_name="B",
            role="R",
            email="ab@example.com",
            status=ProfileCard.STATUS_PUBLISHED,
        )
        settings_obj = ProfileCardSettings.get_solo()
        settings_obj.auto_update_wallet_passes = True
        settings_obj.save(update_fields=["auto_update_wallet_passes"])

        self.client.force_login(self.superuser)
        response = self.client.post(
            reverse("profile_cards:admin_dashboard"),
            {"action": "bump_template_version", "template_id": str(template.id)},
        )
        self.assertEqual(response.status_code, 302)
        template.refresh_from_db()
        card.refresh_from_db()
        self.assertEqual(template.version, 2)
        self.assertEqual(card.applied_template_version, 2)

    def test_create_template_action(self):
        self.client.force_login(self.superuser)
        response = self.client.post(
            reverse("profile_cards:admin_dashboard"),
            {
                "action": "create_template",
                "template_name": "Blue",
                "company_name": "Noir",
                "primary_color": "#0000ff",
                "secondary_color": "#ffffff",
                "is_default_template": "on",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(CardTemplate.objects.filter(name="Blue", is_default=True).exists())

    def test_admin_dashboard_contains_advanced_builder_preview(self):
        self.client.force_login(self.superuser)
        response = self.client.get(reverse("profile_cards:admin_dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "DESIGN STUDIO")
        self.assertContains(response, "preview-screen")
        self.assertContains(response, "updatePreview")
