import re
from datetime import datetime
from typing import Optional

from .reference_data import DATE_FORMATS_BY_COUNTRY

def calculate_mrz_check_digit(data: str) -> str:
    """
    Calcola il checksum per una stringa di dati MRZ secondo lo standard ICAO 9303.
    """
    weights = [7, 3, 1]
    char_map = {str(i): i for i in range(10)}
    char_map.update({chr(ord('A') + i): 10 + i for i in range(26)})
    char_map['<'] = 0

    total = 0
    for i, char in enumerate(data):
        total += char_map[char.upper()] * weights[i % 3]

    return str(total % 10)

def validate_mrz(mrz_line: str) -> bool:
    """
    Valida una linea MRZ controllando i suoi checksum.
    Questo è un esempio semplificato per un passaporto (TD3 formato 2 linee).
    Assume che la linea passata sia la seconda linea della MRZ.
    """
    # Esempio per la seconda linea di un passaporto TD3
    # Formato: [Numero Passaporto][Checksum][Nazionalità][Data Nascita][Checksum][Sesso][Data Scadenza][Checksum][Dati Personali Opzionali][Checksum][Checksum Finale]

    if len(mrz_line) != 44:
        return False

    # 1. Controllo numero documento
    doc_number = mrz_line[0:9]
    doc_check_digit = mrz_line[9]
    if calculate_mrz_check_digit(doc_number) != doc_check_digit:
        return False

    # 2. Controllo data di nascita
    birth_date = mrz_line[13:19]
    birth_check_digit = mrz_line[19]
    if calculate_mrz_check_digit(birth_date) != birth_check_digit:
        return False

    # 3. Controllo data di scadenza
    expiry_date = mrz_line[21:27]
    expiry_check_digit = mrz_line[27]
    if calculate_mrz_check_digit(expiry_date) != expiry_check_digit:
        return False

    # 4. Controllo finale (su quasi tutta la linea)
    final_data = mrz_line[0:10] + mrz_line[13:20] + mrz_line[21:28] + mrz_line[28:43]
    final_check_digit = mrz_line[43]
    if calculate_mrz_check_digit(final_data) != final_check_digit:
        return False

    return True

def validate_italian_id_card_format(doc_number: str) -> bool:
    """Valida il formato della Carta d'Identità Elettronica (CIE) italiana."""
    return re.match(r'^C[A-Z0-9]{2}[0-9]{5}[A-Z0-9]$', doc_number, re.IGNORECASE) is not None

def validate_italian_passport_format(doc_number: str) -> bool:
    """Valida il formato del passaporto italiano."""
    return re.match(r'^[A-Z]{2}[0-9]{7}$', doc_number, re.IGNORECASE) is not None

def validate_italian_driver_license_format(doc_number: str) -> bool:
    """Valida il formato della patente di guida italiana."""
    return re.match(r'^[A-Z0-9]{10}$', doc_number, re.IGNORECASE) is not None


def normalize_date_to_iso(date_str: str, country_code: Optional[str] = None) -> Optional[str]:
    """
    Normalizza una stringa di data nel formato ISO 8601 (YYYY-MM-DD).
    Gestisce formati comuni e include varianti nazionali basate sul codice paese
    (es. separatori con punti o trattini).
    """
    if not date_str:
        return None

    country_formats = DATE_FORMATS_BY_COUNTRY.get((country_code or "").upper(), [])
    base_formats = [
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%Y/%m/%d",
        "%d.%m.%Y",
        "%d %m %Y",
        "%m/%d/%Y",
        "%m-%d-%Y",
        "%m.%d.%Y",
    ]

    seen_formats = set()
    for fmt in country_formats + base_formats:
        if fmt in seen_formats:
            continue
        seen_formats.add(fmt)
        try:
            return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue

    return None
