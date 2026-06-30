import io
import json

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from rest_framework import status
from rest_framework.test import APITestCase
from pypdf import PdfWriter

from hr_portal.models import HREventLog, PayslipBatchPreview


def _create_dummy_pdf():
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    buffer = io.BytesIO()
    writer.write(buffer)
    buffer.seek(0)
    return buffer.getvalue()


class PreviewConfirmCreateFlowTests(APITestCase):
    def setUp(self):
        User = get_user_model()
        self.hr_user = User.objects.create_user(
            username="hr_preview_flow",
            password="pwd",
            role=User.RISORSE_UMANE,
        )
        self.target_user = User.objects.create_user(username="worker_preview_flow", password="pwd")
        self.client.force_authenticate(self.hr_user)

    def test_confirmed_preview_token_is_reused_on_create_and_tracked(self):
        manual_assignments = {
            "segments": {
                "p1": {"user_id": self.target_user.id, "period_label": "2025-01"},
            }
        }

        pdf_bytes = _create_dummy_pdf()

        confirm_payload = {
            "source_file": ContentFile(pdf_bytes, name="payslip.pdf"),
            "manual_assignments": json.dumps(manual_assignments),
        }
        confirm_response = self.client.post(
            "/api/hr/payslip-batches/preview-confirm/",
            confirm_payload,
            format="multipart",
        )
        self.assertEqual(confirm_response.status_code, status.HTTP_200_OK)
        preview_token = confirm_response.data.get("token")
        self.assertTrue(preview_token)
        self.assertTrue(PayslipBatchPreview.objects.filter(pk=preview_token).exists())

        create_payload = {
            "source_file": ContentFile(pdf_bytes, name="payslip.pdf"),
            "preview_token": preview_token,
            "auto_match_strategy": "fiscal_code",
            "enable_ocr": False,
            "ocr_languages": "ita+eng",
        }
        create_response = self.client.post("/api/hr/payslip-batches/", create_payload, format="multipart")

        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED, create_response.data)
        self.assertEqual(
            create_response.data.get("manual_assignments", {}).get("segments", {}).get("p1", {}).get("user_id"),
            str(self.target_user.id),
        )
        self.assertFalse(PayslipBatchPreview.objects.filter(pk=preview_token).exists())

        event = HREventLog.objects.filter(event_type="payslip_batch_created").order_by("-created_at").first()
        self.assertIsNotNone(event)
        metadata = event.metadata or {}
        self.assertEqual(metadata.get("preview_token"), preview_token)
        self.assertTrue(metadata.get("has_preview_token"))
