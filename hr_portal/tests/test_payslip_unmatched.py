import io
from django.contrib.auth import get_user_model
from unittest.mock import patch, MagicMock
from django.core.files.base import ContentFile
from rest_framework import status
from rest_framework.test import APITestCase
from pypdf import PdfWriter

from hr_portal.models import Payslip, PayslipBatch, PayslipUnmatched


def _create_dummy_pdf(content="Test PDF content"):
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)

    # Create an in-memory byte stream
    pdf_buffer = io.BytesIO()
    writer.write(pdf_buffer)
    pdf_buffer.seek(0)

    return pdf_buffer.getvalue()


class PayslipUnmatchedResolveTests(APITestCase):
    def setUp(self):
        User = get_user_model()
        self.hr_user = User.objects.create_user(username="hr_user", password="pwd", role=User.RISORSE_UMANE)
        self.target_user = User.objects.create_user(username="worker", password="pwd")

        self.batch = PayslipBatch.objects.create(
            source_file=ContentFile(b"batch", name="batch.zip"),
            uploaded_by=self.hr_user,
        )
        self.unmatched = PayslipUnmatched.objects.create(
            batch=self.batch,
            identifier="ABC123",
            file=ContentFile(_create_dummy_pdf(), name="payslip.pdf"),
        )

    def test_resolve_accepts_username_identifier(self):
        self.client.force_authenticate(self.hr_user)
        url = f"/api/hr/payslip-unmatched/{self.unmatched.id}/resolve/"

        response = self.client.post(url, {"user": self.target_user.username, "period_label": "2025-01"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.unmatched.refresh_from_db()
        self.assertTrue(self.unmatched.resolved)
        self.assertEqual(self.unmatched.resolved_to_id, self.target_user.id)
        self.assertEqual(response.data["payslip"]["user"], self.target_user.id)

        payslip_path = response.data["payslip"]["file"]
        self.assertIn("hr/payslips/", payslip_path)
        self.assertNotIn("hr/payslips/hr/payslips", payslip_path)

    def test_resolve_returns_not_found_for_unknown_identifier(self):
        self.client.force_authenticate(self.hr_user)
        url = f"/api/hr/payslip-unmatched/{self.unmatched.id}/resolve/"

        response = self.client.post(url, {"user": "unknown-user"})

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.unmatched.refresh_from_db()
        self.assertFalse(self.unmatched.resolved)

    def test_resolve_returns_error_when_file_missing(self):
        self.client.force_authenticate(self.hr_user)
        url = f"/api/hr/payslip-unmatched/{self.unmatched.id}/resolve/"

        # Simulate a missing file on storage
        self.unmatched.file.delete(save=False)

        response = self.client.post(url, {"user": self.target_user.username})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("detail", response.data)
        self.unmatched.refresh_from_db()
        self.assertFalse(self.unmatched.resolved)

    def test_resolve_handles_invalid_pdf(self):
        self.client.force_authenticate(self.hr_user)
        url = f"/api/hr/payslip-unmatched/{self.unmatched.id}/resolve/"

        self.unmatched.file.save("broken.pdf", ContentFile(b"not a pdf"), save=True)

        response = self.client.post(url, {"user": self.target_user.username})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.unmatched.refresh_from_db()
        self.assertTrue(self.unmatched.resolved)

    def test_resolve_recovers_legacy_basename_paths(self):
        self.client.force_authenticate(self.hr_user)
        url = f"/api/hr/payslip-unmatched/{self.unmatched.id}/resolve/"

        # Re-save the file under the expected upload_to path but strip the stored name
        self.unmatched.file.save("weird.pdf", ContentFile(b"legacy"), save=True)
        self.unmatched.file.name = "weird.pdf"
        self.unmatched.save(update_fields=["file"])

        with patch('hr_portal.models.PdfReader') as mock_reader:
            mock_reader.return_value = MagicMock(pages=[])
            response = self.client.post(url, {"user": self.target_user.username})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.unmatched.refresh_from_db()
        self.assertTrue(self.unmatched.resolved)

    def test_resolve_truncates_long_filenames(self):
        self.client.force_authenticate(self.hr_user)

        long_name = (
            "verylongusername.value-with-many-separators-and-unicode_characters__" * 2
            + "COSTAREY102024_BBnvHBx-FNLDRD_hDzQb1Z.pdf"
        )
        self.unmatched.file.save(long_name, ContentFile(b"pdf"), save=True)

        url = f"/api/hr/payslip-unmatched/{self.unmatched.id}/resolve/"
        with patch('hr_portal.models.PdfReader') as mock_reader:
            mock_reader.return_value = MagicMock(pages=[])
            response = self.client.post(url, {"user": self.target_user.username, "period_label": "2025-02"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payslip_path = response.data["payslip"]["file"]
        self.assertIn("hr/payslips/", payslip_path)

        payslip = Payslip.objects.get(pk=response.data["payslip"]["id"])
        # Ensure the stored name respects the FileField max_length
        self.assertLessEqual(len(payslip.file.name), payslip.file.field.max_length)
