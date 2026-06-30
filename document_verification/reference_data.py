"""
Dati di riferimento per la verifica dei documenti d'identità.
Raccoglie pattern, campi obbligatori, presenza di MRZ e suggerimenti lingua.
"""
from dataclasses import dataclass
from typing import Dict, List, Optional

# Tipologie di documento standardizzate per la tabella di riferimento
CANONICAL_DOC_TYPES = {
    "ID_CARD": "ID_CARD",
    "ID_CARD_CIE": "ID_CARD",
    "PASSPORT": "PASSPORT",
    "DRIVER_LICENSE": "DRIVER_LICENSE",
    "LICENSE": "DRIVER_LICENSE",
}


def normalize_document_type(document_type: Optional[str]) -> Optional[str]:
    if not document_type:
        return None
    return CANONICAL_DOC_TYPES.get(document_type.upper(), document_type.upper())


@dataclass(frozen=True)
class DocumentBlueprint:
    document_number_pattern: str
    required_fields: List[str]
    has_mrz: bool
    mrz_position: str
    date_formats: List[str]
    language_hints: List[str]


DOCUMENT_FIELD_REFERENCE: Dict[str, Dict[str, DocumentBlueprint]] = {
    "ITA": {
        "ID_CARD": DocumentBlueprint(
            document_number_pattern=r"^C[A-Z][0-9]{7}$",
            required_fields=["document_number", "first_name", "last_name", "birth_date", "issuer_country"],
            has_mrz=False,
            mrz_position="Retro tessera, area bassa su due righe",
            date_formats=["%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y"],
            language_hints=["ita", "latn", "eng"],
        ),
        "PASSPORT": DocumentBlueprint(
            document_number_pattern=r"^[A-Z]{2}[0-9]{7}$",
            required_fields=["document_number", "first_name", "last_name", "birth_date", "expiry_date", "issuer_country"],
            has_mrz=True,
            mrz_position="Pagina dati, bordo inferiore (2 righe)",
            date_formats=["%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y"],
            language_hints=["ita", "latn", "eng"],
        ),
        "DRIVER_LICENSE": DocumentBlueprint(
            document_number_pattern=r"^[A-Z0-9]{10}$",
            required_fields=["document_number", "first_name", "last_name", "birth_date", "expiry_date", "issuer_country"],
            has_mrz=False,
            mrz_position="Non presente",
            date_formats=["%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y"],
            language_hints=["ita", "latn", "eng"],
        ),
    },
    "FRA": {
        "ID_CARD": DocumentBlueprint(
            document_number_pattern=r"^[0-9]{12}$",
            required_fields=["document_number", "first_name", "last_name", "birth_date", "expiry_date", "issuer_country"],
            has_mrz=True,
            mrz_position="Retro carta, tre righe MRZ",
            date_formats=["%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y"],
            language_hints=["fra", "latn", "eng"],
        ),
        "PASSPORT": DocumentBlueprint(
            document_number_pattern=r"^[0-9]{2}[A-Z]{2}[0-9]{5}$",
            required_fields=["document_number", "first_name", "last_name", "birth_date", "expiry_date", "issuer_country"],
            has_mrz=True,
            mrz_position="Pagina dati, bordo inferiore (2 righe)",
            date_formats=["%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y"],
            language_hints=["fra", "latn", "eng"],
        ),
        "DRIVER_LICENSE": DocumentBlueprint(
            document_number_pattern=r"^[0-9]{12}$",
            required_fields=["document_number", "first_name", "last_name", "birth_date", "expiry_date", "issuer_country"],
            has_mrz=False,
            mrz_position="Non presente",
            date_formats=["%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y"],
            language_hints=["fra", "latn", "eng"],
        ),
    },
    "ESP": {
        "ID_CARD": DocumentBlueprint(
            document_number_pattern=r"^[0-9]{8}[A-Z]$",
            required_fields=["document_number", "first_name", "last_name", "birth_date", "issuer_country"],
            has_mrz=True,
            mrz_position="Retro carta, tre righe MRZ",
            date_formats=["%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y"],
            language_hints=["spa", "latn", "eng"],
        ),
        "PASSPORT": DocumentBlueprint(
            document_number_pattern=r"^[A-Z]{3}[0-9]{6}$",
            required_fields=["document_number", "first_name", "last_name", "birth_date", "expiry_date", "issuer_country"],
            has_mrz=True,
            mrz_position="Pagina dati, bordo inferiore (2 righe)",
            date_formats=["%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y"],
            language_hints=["spa", "latn", "eng"],
        ),
        "DRIVER_LICENSE": DocumentBlueprint(
            document_number_pattern=r"^[0-9]{8}[A-Z]{0,2}$",
            required_fields=["document_number", "first_name", "last_name", "birth_date", "expiry_date", "issuer_country"],
            has_mrz=False,
            mrz_position="Non presente",
            date_formats=["%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y"],
            language_hints=["spa", "latn", "eng"],
        ),
    },
}


DATE_FORMATS_BY_COUNTRY: Dict[str, List[str]] = {
    country: {
        fmt for profile in country_data.values() for fmt in profile.date_formats
    }
    for country, country_data in DOCUMENT_FIELD_REFERENCE.items()
}

# Convert set back to list to maintain typing
DATE_FORMATS_BY_COUNTRY = {k: list(v) for k, v in DATE_FORMATS_BY_COUNTRY.items()}


def get_document_blueprint(country_code: Optional[str], document_type: Optional[str]) -> Optional[DocumentBlueprint]:
    if not country_code or not document_type:
        return None
    canonical_type = normalize_document_type(document_type)
    country_profiles = DOCUMENT_FIELD_REFERENCE.get(country_code.upper())
    if not country_profiles:
        return None
    return country_profiles.get(canonical_type)


def get_language_hints(country_code: Optional[str]) -> List[str]:
    if not country_code:
        return []
    country_profiles = DOCUMENT_FIELD_REFERENCE.get(country_code.upper())
    if not country_profiles:
        return []
    # Prefer language hints of passport profile if available as più completa
    passport_profile = country_profiles.get("PASSPORT")
    if passport_profile:
        return passport_profile.language_hints
    # Otherwise fallback to first profile languages
    first_profile = next(iter(country_profiles.values()))
    return first_profile.language_hints
