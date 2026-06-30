from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from .models import VerifiedDocument
from .services import DocumentVerificationService, MockOcrService

class DocumentVerificationAPITests(APITestCase):

    def test_verify_valid_id_card(self):
        """
        Testa la verifica di una carta d'identità valida.
        """
        url = reverse('document_verification_api:verify_document')
        data = {'image_id': 'VALID_ID_CARD'}
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(VerifiedDocument.objects.count(), 1)

        doc = VerifiedDocument.objects.first()
        self.assertEqual(doc.status, VerifiedDocument.VerificationStatus.VERIFIED)
        self.assertEqual(doc.document_number, "CA1234567")
        self.assertEqual(doc.first_name, "MARIO")
        self.assertEqual(doc.last_name, "ROSSI")

    def test_verify_low_confidence_passport(self):
        """
        Testa un documento con bassa confidenza che richiede revisione manuale.
        """
        url = reverse('document_verification_api:verify_document')
        data = {'image_id': 'LOW_CONFIDENCE_PASSPORT'}
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(VerifiedDocument.objects.count(), 1)

        doc = VerifiedDocument.objects.first()
        self.assertEqual(doc.status, VerifiedDocument.VerificationStatus.NEEDS_REVIEW)
        self.assertIn("Bassa confidenza per il campo 'first_name'", doc.review_notes)
        self.assertIn("Bassa confidenza per il campo 'birth_date'", doc.review_notes)

    def test_verify_missing_fields_driver_license(self):
        """
        Testa un documento con campi mancanti che richiede revisione manuale.
        """
        url = reverse('document_verification_api:verify_document')
        data = {'image_id': 'MISSING_FIELDS_DRIVER_LICENSE'}
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(VerifiedDocument.objects.count(), 1)

        doc = VerifiedDocument.objects.first()
        self.assertEqual(doc.status, VerifiedDocument.VerificationStatus.NEEDS_REVIEW)
        self.assertIn("Campo obbligatorio mancante: 'expiry_date'", doc.review_notes)

    def test_missing_image_id(self):
        """
        Testa una richiesta senza 'image_id'.
        """
        url = reverse('document_verification_api:verify_document')
        data = {}
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(VerifiedDocument.objects.count(), 0)

    def test_verify_passport_with_valid_mrz(self):
        """
        Testa un passaporto con una MRZ valida.
        """
        url = reverse('document_verification_api:verify_document')
        data = {'image_id': 'PASSPORT_WITH_VALID_MRZ'}
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        doc = VerifiedDocument.objects.first()
        self.assertEqual(doc.status, VerifiedDocument.VerificationStatus.VERIFIED)

    def test_verify_passport_with_invalid_mrz(self):
        """
        Testa un passaporto con una MRZ non valida che richiede revisione.
        """
        url = reverse('document_verification_api:verify_document')
        data = {'image_id': 'PASSPORT_WITH_INVALID_MRZ'}
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        doc = VerifiedDocument.objects.first()
        self.assertEqual(doc.status, VerifiedDocument.VerificationStatus.NEEDS_REVIEW)
        self.assertIn("Validazione checksum MRZ fallita.", doc.review_notes)

    def test_expected_mrz_missing(self):
        url = reverse('document_verification_api:verify_document')
        data = {
            'image_id': 'SPANISH_PASSPORT_WITHOUT_MRZ',
            'issuer_country': 'ESP',
            'document_type': 'PASSPORT',
        }
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        doc = VerifiedDocument.objects.first()
        self.assertEqual(doc.status, VerifiedDocument.VerificationStatus.NEEDS_REVIEW)
        self.assertIn('MRZ attesa ma non trovata', doc.review_notes)

    def test_country_specific_date_normalization(self):
        url = reverse('document_verification_api:verify_document')
        data = {
            'image_id': 'FRENCH_ID_WITH_DOTS',
            'issuer_country': 'FRA',
            'document_type': 'ID_CARD',
        }
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        doc = VerifiedDocument.objects.first()
        self.assertEqual(str(doc.birth_date), '1995-12-31')
        self.assertEqual(str(doc.expiry_date), '2030-12-31')

    def test_language_hints_are_forwarded(self):
        mock_service = MockOcrService()
        verification_service = DocumentVerificationService(ocr_service=mock_service)

        verification_service.verify_document(
            image_id='VALID_ID_CARD',
            issuer_country='ITA',
            document_type='ID_CARD',
        )

        self.assertEqual(mock_service.last_language_hints, ['ita', 'latn', 'eng'])
