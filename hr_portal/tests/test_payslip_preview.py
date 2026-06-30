import io
import json

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from rest_framework import status
from rest_framework.test import APITestCase
from pypdf import PdfWriter


def _create_dummy_pdf():
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    buffer = io.BytesIO()
    writer.write(buffer)
    buffer.seek(0)
    return buffer.getvalue()


class PayslipPreviewTests(APITestCase):
    def setUp(self):
        User = get_user_model()
        self.hr_user = User.objects.create_user(
            username="hr_user",
            password="pwd",
            role=User.RISORSE_UMANE,
        )
        self.target_user = User.objects.create_user(username="worker", password="pwd")

    def test_preview_accepts_manual_assignments(self):
        self.client.force_authenticate(self.hr_user)
        payload = {
            "source_file": ContentFile(_create_dummy_pdf(), name="payslip.pdf"),
            "manual_assignments": json.dumps(
                {
                    "segments": {
                        "p1": {"user_id": self.target_user.id, "period_label": "2025-01"},
                    }
                }
            ),
        }
        response = self.client.post("/api/hr/payslip-batches/preview/", payload, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        segments = response.data.get("segments", [])
        self.assertEqual(len(segments), 1)
        segment = segments[0]
        self.assertTrue(segment["manual_assigned"])
        self.assertEqual(segment["user"]["id"], self.target_user.id)
        self.assertEqual(segment["manual_period_label"], "2025-01")
        self.assertIn("preview_pages", segment)
        self.assertIn("preview_available", segment)
        self.assertEqual(response.data.get("capabilities", {}).get("schema_version"), "v2")

    def test_preview_rejects_invalid_period(self):
        self.client.force_authenticate(self.hr_user)
        payload = {
            "source_file": ContentFile(_create_dummy_pdf(), name="payslip.pdf"),
            "manual_assignments": json.dumps(
                {
                    "segments": {
                        "p1": {"user_id": self.target_user.id, "period_label": "2025-13"},
                    }
                }
            ),
        }
        response = self.client.post("/api/hr/payslip-batches/preview/", payload, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_preview_returns_error_code_for_missing_file(self):
        self.client.force_authenticate(self.hr_user)
        response = self.client.post("/api/hr/payslip-batches/preview/", {}, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data.get("error_code"), "missing_source_file")

    def test_preview_returns_error_code_for_unsupported_file_type(self):
        self.client.force_authenticate(self.hr_user)
        payload = {
            "source_file": ContentFile(b"not-a-pdf", name="notes.txt"),
        }
        response = self.client.post("/api/hr/payslip-batches/preview/", payload, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data.get("error_code"), "unsupported_file_type")

    def test_preview_start_rejects_unsupported_file_type(self):
        self.client.force_authenticate(self.hr_user)
        payload = {
            "source_file": ContentFile(b"not-a-pdf", name="notes.txt"),
        }
        response = self.client.post("/api/hr/payslip-batches/preview-start/", payload, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data.get("error_code"), "unsupported_file_type")


    def test_preview_status_includes_segment_preview_pages(self):
        self.client.force_authenticate(self.hr_user)
        start_payload = {
            "source_file": ContentFile(_create_dummy_pdf(), name="payslip.pdf"),
        }
        start_response = self.client.post("/api/hr/payslip-batches/preview-start/", start_payload, format="multipart")
        self.assertEqual(start_response.status_code, status.HTTP_201_CREATED)
        token = start_response.data["token"]

        from hr_portal.models import PayslipPreviewJob
        job = PayslipPreviewJob.objects.get(pk=token)
        job.preview_payload = {
            "segments": [{"segment_key": "p1", "page_start": 1, "page_end": 1}],
            "scan_pages": [{"page_index": 1, "image_url": "/media/p1.png"}],
        }
        job.status = PayslipPreviewJob.STATUS_COMPLETED
        job.save(update_fields=["preview_payload", "status", "updated_at"])

        response = self.client.get(f"/api/hr/payslip-batches/preview-status/{token}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        segment = response.data["preview"]["segments"][0]
        self.assertTrue(segment["preview_available"])
        self.assertEqual(len(segment["preview_pages"]), 1)

    def test_preview_status_sets_segment_preview_unavailable_code(self):
        self.client.force_authenticate(self.hr_user)
        start_payload = {
            "source_file": ContentFile(_create_dummy_pdf(), name="payslip.pdf"),
        }
        start_response = self.client.post("/api/hr/payslip-batches/preview-start/", start_payload, format="multipart")
        self.assertEqual(start_response.status_code, status.HTTP_201_CREATED)
        token = start_response.data["token"]

        from hr_portal.models import PayslipPreviewJob
        job = PayslipPreviewJob.objects.get(pk=token)
        job.preview_payload = {
            "segments": [{"segment_key": "p1", "page_start": 1, "page_end": 1}],
            "scan_pages": [],
        }
        job.status = PayslipPreviewJob.STATUS_COMPLETED
        job.save(update_fields=["preview_payload", "status", "updated_at"])

        response = self.client.get(f"/api/hr/payslip-batches/preview-status/{token}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        segment = response.data["preview"]["segments"][0]
        self.assertFalse(segment["preview_available"])
        self.assertEqual(segment["preview_error_code"], "segment_preview_unavailable")


    def test_preview_status_preserves_existing_segment_preview_pages(self):
        self.client.force_authenticate(self.hr_user)
        start_payload = {
            "source_file": ContentFile(_create_dummy_pdf(), name="payslip.pdf"),
        }
        start_response = self.client.post("/api/hr/payslip-batches/preview-start/", start_payload, format="multipart")
        self.assertEqual(start_response.status_code, status.HTTP_201_CREATED)
        token = start_response.data["token"]

        from hr_portal.models import PayslipPreviewJob

        job = PayslipPreviewJob.objects.get(pk=token)
        job.preview_payload = {
            "segments": [
                {
                    "segment_key": "p1",
                    "page_start": 1,
                    "page_end": 1,
                    "preview_pages": [{"page_index": 1, "image_url": "/media/custom.png"}],
                    "preview_available": True,
                }
            ],
            "capabilities": {"schema_version": "v1"},
        }
        job.status = PayslipPreviewJob.STATUS_COMPLETED
        job.save(update_fields=["preview_payload", "status", "updated_at"])

        response = self.client.get(f"/api/hr/payslip-batches/preview-status/{token}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        segment = response.data["preview"]["segments"][0]
        self.assertEqual(segment["preview_pages"][0]["image_url"], "/media/custom.png")
        self.assertTrue(segment["preview_available"])
        self.assertEqual(response.data["preview"]["capabilities"].get("schema_version"), "v2")
