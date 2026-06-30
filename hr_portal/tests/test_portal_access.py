from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from unittest.mock import patch

from hr_portal.models import HRDocument, HRNotification


class HRPortalAccessTests(APITestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="employee", password="pass1234")

    def test_documents_list_available_for_authenticated_user(self):
        document = HRDocument.objects.create(
            title="Policy ferie",
            description="",
            file=ContentFile(b"dummy", name="policy.pdf"),
            visible_from=timezone.now() - timezone.timedelta(days=1),
        )
        self.client.force_authenticate(self.user)

        response = self.client.get("/api/hr/documents/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        payload = response.data[0]
        self.assertEqual(payload["id"], str(document.pk))
        self.assertTrue(payload["file_name"].startswith("policy"))
        self.assertTrue(payload["file_name"].endswith(".pdf"))
        self.assertTrue(payload["file"].endswith(".pdf"))

    def test_documents_list_handles_missing_file(self):
        document = HRDocument.objects.create(
            title="Cedolino",
            description="",
            file=ContentFile(b"dummy", name="cedolino.pdf"),
            visible_from=timezone.now() - timezone.timedelta(days=1),
        )
        # simulate missing file on disk
        document.file.delete(save=False)
        document.file = ""
        document.save(update_fields=["file"])

        self.client.force_authenticate(self.user)
        response = self.client.get("/api/hr/documents/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        payload = response.data[0]
        self.assertIsNone(payload["file"])
        self.assertIsNone(payload.get("file_name"))

    def test_notifications_visible_to_end_users(self):
        notification = HRNotification.objects.create(
            title="Benvenuto",
            body="Messaggio di prova",
            status=HRNotification.STATUS_PUBLISHED,
            scheduled_for=timezone.now() - timezone.timedelta(hours=1),
            expires_at=None,
        )

        self.client.force_authenticate(self.user)
        response = self.client.get("/api/hr/notifications/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], str(notification.pk))

    @patch("django_vite.templatetags.django_vite.DjangoViteAssetLoader.instance")
    def test_portal_root_available_for_hr_users(self, vite_loader_instance):
        vite_loader_instance.return_value.generate_vite_asset.return_value = ""
        User = get_user_model()
        hr_user = User.objects.create_user(username="hr_portal_user", password="pass1234", role=User.RISORSE_UMANE)
        self.client.login(username="hr_portal_user", password="pass1234")

        response = self.client.get(reverse("hr_portal:portal"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
