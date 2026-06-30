import re

from .ocr_data import OcrResult
from .reference_data import get_document_blueprint, get_language_hints, normalize_document_type

class MockOcrService:
    """
    Servizio OCR simulato per lo sviluppo e il test.
    Restituisce dati di esempio basati su un ID di test.
    """

    def extract_data(self, image_id: str, language_hints=None, country_code: str = None, document_type: str = None) -> OcrResult:
        """
        Simula l'estrazione di dati OCR da un'immagine.
        """
        self.last_language_hints = language_hints or []
        self.last_country_code = country_code
        self.last_document_type = document_type
        if image_id == "VALID_ID_CARD":
            return self._get_valid_id_card_data()
        elif image_id == "LOW_CONFIDENCE_PASSPORT":
            return self._get_low_confidence_passport_data()
        elif image_id == "MISSING_FIELDS_DRIVER_LICENSE":
            return self._get_missing_fields_driver_license_data()
        elif image_id == "PASSPORT_WITH_VALID_MRZ":
            return self._get_passport_with_valid_mrz()
        elif image_id == "PASSPORT_WITH_INVALID_MRZ":
            return self._get_passport_with_invalid_mrz()
        elif image_id == "SPANISH_PASSPORT_WITHOUT_MRZ":
            return self._get_spanish_passport_without_mrz()
        elif image_id == "FRENCH_ID_WITH_DOTS":
            return self._get_french_id_with_dotted_date()
        else:
            return self._get_default_error_data()

    def _get_valid_id_card_data(self) -> OcrResult:
        return OcrResult(
            document_number="CA1234567",
            first_name="MARIO",
            last_name="ROSSI",
            birth_date="1980-01-15",
            expiry_date="2030-01-14",
            issuer_country="ITA",
            confidence_scores={
                "document_number": 0.99,
                "first_name": 0.98,
                "last_name": 0.97,
                "birth_date": 0.99,
                "expiry_date": 0.96,
                "issuer_country": 0.99
            },
            raw_response={"document_type": "ID_CARD_CIE"}
        )

    def _get_low_confidence_passport_data(self) -> OcrResult:
        return OcrResult(
            document_number="YA8765432",
            first_name="LUIGI",
            last_name="VERDI",
            birth_date="1992-05-20",
            expiry_date="2028-05-19",
            issuer_country="ITA",
            confidence_scores={
                "document_number": 0.92,
                "first_name": 0.85, # Confidenza bassa
                "last_name": 0.91,
                "birth_date": 0.78, # Confidenza bassa
                "expiry_date": 0.93,
                "issuer_country": 0.95
            },
            raw_response={"document_type": "PASSPORT"}
        )

    def _get_missing_fields_driver_license_data(self) -> OcrResult:
        return OcrResult(
            document_number="U1A234567B",
            first_name="ANNA",
            last_name="BIANCHI",
            birth_date="1985-11-30",
            expiry_date=None,  # Campo mancante
            issuer_country="ITA",
            confidence_scores={
                "document_number": 0.99,
                "first_name": 0.98,
                "last_name": 0.98,
                "birth_date": 0.99,
                "issuer_country": 0.97
            },
            raw_response={"document_type": "DRIVER_LICENSE"}
        )

    def _get_default_error_data(self) -> OcrResult:
        return OcrResult(
            confidence_scores={},
            raw_response={"error": "Document not recognized"}
        )

    def _get_passport_with_valid_mrz(self) -> OcrResult:
        return OcrResult(
            document_number="YA1234567",
            first_name="MARIO",
            last_name="ROSSI",
            birth_date="1980-01-15",
            expiry_date="2030-01-14",
            issuer_country="ITA",
            confidence_scores={"document_number": 0.99, "first_name": 0.99, "last_name": 0.99, "birth_date": 0.99, "expiry_date": 0.99, "issuer_country": 0.99},
            raw_response={
                "document_type": "PASSPORT",
                # MRZ con numero di documento e checksum ricalcolati e corretti
                "mrz_line_2": "YA12345676ITA8001151M3001145<<<<<<<<<<<<<<<2"
            }
        )

    def _get_passport_with_invalid_mrz(self) -> OcrResult:
        return OcrResult(
            document_number="YA1234567",
            first_name="MARIO",
            last_name="ROSSI",
            birth_date="1980-01-15",
            expiry_date="2030-01-14",
            issuer_country="ITA",
            confidence_scores={"document_number": 0.99, "first_name": 0.99, "last_name": 0.99, "birth_date": 0.99, "expiry_date": 0.99, "issuer_country": 0.99},
            raw_response={
                "document_type": "PASSPORT",
                # Stessa MRZ di sopra, ma con il checksum finale errato (9 invece di 2)
                "mrz_line_2": "YA12345676ITA8001151M3001145<<<<<<<<<<<<<<<9"
            }
        )

    def _get_spanish_passport_without_mrz(self) -> OcrResult:
        return OcrResult(
            document_number="ABC123456",
            first_name="JUAN",
            last_name="GARCIA",
            birth_date="1990/07/12",
            expiry_date="2030/07/11",
            issuer_country="ESP",
            confidence_scores={
                "document_number": 0.98,
                "first_name": 0.98,
                "last_name": 0.98,
                "birth_date": 0.95,
                "expiry_date": 0.95,
                "issuer_country": 0.95,
            },
            raw_response={"document_type": "PASSPORT"},
        )

    def _get_french_id_with_dotted_date(self) -> OcrResult:
        return OcrResult(
            document_number="123456789012",
            first_name="JULIE",
            last_name="DURAND",
            birth_date="31.12.1995",
            expiry_date="31.12.2030",
            issuer_country="FRA",
            confidence_scores={
                "document_number": 0.97,
                "first_name": 0.97,
                "last_name": 0.97,
                "birth_date": 0.96,
                "expiry_date": 0.96,
                "issuer_country": 0.97,
            },
            raw_response={"document_type": "ID_CARD"},
        )

def get_ocr_service(provider_name: str = "mock"):
    """
    Factory per ottenere un'istanza del servizio OCR.
    In futuro, potrà restituire client per servizi reali come Google o AWS.
    """
    if provider_name == "mock":
        return MockOcrService()
    # Esempio futuro:
    # elif provider_name == "google":
    #     return GoogleOcrService()
    else:
        raise ValueError(f"Provider OCR non supportato: {provider_name}")

from .models import VerifiedDocument
from . import validators

class DocumentVerificationService:
    """
    Servizio per orchestrare il processo di verifica dei documenti.
    """
    def __init__(self, ocr_service, confidence_threshold=0.95):
        self.ocr_service = ocr_service
        self.confidence_threshold = confidence_threshold

    def verify_document(self, image_id: str, issuer_country: str = None, document_type: str = None) -> VerifiedDocument:
        # 1. Estrai i dati con il servizio OCR
        country_hint = (issuer_country or "").upper() or None
        document_type_hint = normalize_document_type(document_type)
        language_hints = get_language_hints(country_hint)
        ocr_result = self.ocr_service.extract_data(
            image_id=image_id,
            language_hints=language_hints,
            country_code=country_hint,
            document_type=document_type_hint,
        )

        # Crea l'oggetto nel database
        verified_doc = VerifiedDocument.objects.create(
            raw_ocr_response=ocr_result.raw_response,
            confidence_scores=ocr_result.confidence_scores,
        )

        review_notes = []

        # Determina le informazioni di contesto
        issuer_country_code = (ocr_result.issuer_country or country_hint or "").upper() or None
        raw_response = ocr_result.raw_response or {}
        doc_type_raw = raw_response.get("document_type") or document_type_hint
        normalized_doc_type = normalize_document_type(doc_type_raw)
        blueprint = get_document_blueprint(issuer_country_code, normalized_doc_type)

        # 2. Normalizzazione e validazione dei campi

        # Normalizza le date
        birth_date = validators.normalize_date_to_iso(ocr_result.birth_date, issuer_country_code)
        expiry_date = validators.normalize_date_to_iso(ocr_result.expiry_date, issuer_country_code)

        verified_doc.birth_date = birth_date
        verified_doc.expiry_date = expiry_date
        verified_doc.document_number = ocr_result.document_number
        verified_doc.first_name = ocr_result.first_name
        verified_doc.last_name = ocr_result.last_name
        verified_doc.issuer_country = issuer_country_code

        # 3. Controllo della confidenza
        for field, score in ocr_result.confidence_scores.items():
            if score < self.confidence_threshold:
                review_notes.append(f"Bassa confidenza per il campo '{field}': {score:.2f}")

        # 4. Controllo campi mancanti
        required_fields = blueprint.required_fields if blueprint else ['document_number', 'first_name', 'last_name', 'birth_date', 'expiry_date']
        for field in required_fields:
            if not getattr(ocr_result, field):
                review_notes.append(f"Campo obbligatorio mancante: '{field}'")

        # 5. Applica validatori specifici
        doc_number = ocr_result.document_number

        if doc_number:
            if blueprint and not re.match(blueprint.document_number_pattern, doc_number):
                review_notes.append(
                    f"Formato numero documento non valido per {issuer_country_code or 'paese sconosciuto'} ({normalized_doc_type or 'tipo sconosciuto'}): {doc_number}"
                )
            elif normalized_doc_type == "ID_CARD" and issuer_country_code == "ITA" and not validators.validate_italian_id_card_format(doc_number):
                review_notes.append(f"Formato numero CIE non valido: {doc_number}")
            elif normalized_doc_type == "PASSPORT" and issuer_country_code == "ITA" and not validators.validate_italian_passport_format(doc_number):
                review_notes.append(f"Formato numero passaporto non valido: {doc_number}")
            elif normalized_doc_type == "DRIVER_LICENSE" and issuer_country_code == "ITA" and not validators.validate_italian_driver_license_format(doc_number):
                review_notes.append(f"Formato numero patente non valido: {doc_number}")

        # Validazione MRZ (se presente)
        mrz_line_2 = raw_response.get("mrz_line_2")
        if blueprint and blueprint.has_mrz and not mrz_line_2:
            review_notes.append(
                f"MRZ attesa ma non trovata. Posizione tipica: {blueprint.mrz_position}."
            )
        if mrz_line_2 and not validators.validate_mrz(mrz_line_2):
            review_notes.append(f"Validazione checksum MRZ fallita.")

        # 6. Determina lo stato finale
        if review_notes:
            verified_doc.status = VerifiedDocument.VerificationStatus.NEEDS_REVIEW
            verified_doc.review_notes = "\n".join(review_notes)
        else:
            verified_doc.status = VerifiedDocument.VerificationStatus.VERIFIED

        verified_doc.save()
        return verified_doc
