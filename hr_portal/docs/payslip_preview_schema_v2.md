# Payslip Preview Schema v2

## Obiettivo
Contratto dati aggiornato per la preview segmentata nel Portale HR.

## Campi segmento (v2)
Ogni elemento in `preview.segments[]` include:

- `preview_pages`: lista immagini disponibili per il range `page_start..page_end`.
- `preview_available`: boolean (`true` se `preview_pages` non vuoto).
- `preview_error_code`: valorizzato a `segment_preview_unavailable` quando non ci sono immagini e non esiste già un errore segmento.

## Retrocompatibilità
- Se il backend riceve segmenti già con `preview_pages`, i valori vengono preservati.
- Se `preview_pages` manca, viene derivato da `scan_pages` (quando disponibile).
- La capability `schema_version` viene normalizzata a `v2`.

## Esempio
```json
{
  "preview": {
    "capabilities": {
      "schema_version": "v2",
      "mode": "async"
    },
    "scan_pages": [
      { "page_index": 1, "image_url": "/media/p1.png" }
    ],
    "segments": [
      {
        "segment_key": "p1",
        "page_start": 1,
        "page_end": 1,
        "preview_pages": [
          { "page_index": 1, "image_url": "/media/p1.png" }
        ],
        "preview_available": true
      }
    ]
  }
}
```
