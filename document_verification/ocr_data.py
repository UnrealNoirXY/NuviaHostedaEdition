from dataclasses import dataclass, field
from typing import Optional, Dict

@dataclass
class OcrResult:
    """
    Struttura dati standard per contenere i risultati dell'estrazione OCR.
    """
    document_number: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    birth_date: Optional[str] = None  # Formato YYYY-MM-DD
    expiry_date: Optional[str] = None # Formato YYYY-MM-DD
    issuer_country: Optional[str] = None # Codice ISO 3166-1 alpha-3

    # Punteggi di confidenza per ogni campo estratto
    confidence_scores: Dict[str, float] = field(default_factory=dict)

    # Dati grezzi restituiti dal motore OCR
    raw_response: Dict = field(default_factory=dict)
