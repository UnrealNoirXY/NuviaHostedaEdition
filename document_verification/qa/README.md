# QA plan documentale

Questo piano copre raccolta dataset, smoke test automatizzati e validazione cross-device per il flusso di verifica documenti.

## 1. Raccolta dataset (minimo 10–20 immagini per combinazione paese/tipo)
- **Copertura obbligatoria:** Carta d'identità, passaporto e patente per ciascun paese target (ITA, ESP, FRA). Aggiungere altri paesi replicando la struttura del manifest.
- **Varianza di cattura:** includere per ogni combinazione almeno: fronte/retro, luce naturale e artificiale, riflessi e bagliori, angoli obliqui (10–25°), tagli parziali, foto leggermente sfocate e documenti plastificati.
- **Dati sensibili:** usare documenti sintetici o autorizzati; oscurare PII dove non necessaria alla valutazione OCR; salvare il consenso nel campo `consent_reference` del manifest.
- **Struttura cartelle:** `document_verification/qa/datasets/<PAESE>/<TIPO>/file.jpg`. Usare suffissi descrittivi (`_glare`, `_angle`, `_partial`, `_shadow`).
- **Ground truth:** per ogni file valorizzare nel manifest `expected_fields` (numero documento, nome, cognome, data nascita, data scadenza, paese emittente) e `quality_notes` per annotare difetti visivi.
- **Progress tracking:** aggiornare `status: collected/needs_replacement/pending` nel manifest per avere almeno 10–20 elementi per combinazione.

## 2. Manifest e gestione metadati
- Il file [`dataset_manifest.yaml`](./dataset_manifest.yaml) elenca i campioni richiesti e i tag di difficoltà da garantire.
- Aggiungere nuove voci copiando una scheda esistente; mantenere `capture_tags` coerenti per consentire filtri (es. `glare`, `angled`, `shadow`, `partial_crop`).
- Conservare le immagini localmente (non nel VCS) e indicare solo i percorsi relativi e gli hash nel manifest per verificare l'integrità.

## 3. Smoke test automatizzati
- Configurare i casi nel file [`smoke_test_config.yaml`](./smoke_test_config.yaml): ogni caso definisce `image_id` (o `image_path` se si vuole inviare un file), `issuer_country`, `document_type`, i `expected_fields` e la soglia `min_field_accuracy`.
- Eseguire lo script [`run_smoke_tests.py`](./run_smoke_tests.py) puntando all'istanza backend:
  ```bash
  python document_verification/qa/run_smoke_tests.py \
    --config document_verification/qa/smoke_test_config.yaml \
    --endpoint http://localhost:8000/document_verification/verify/
  ```
- Lo script invia le immagini (o gli `image_id` mock), calcola l'accuratezza per i campi chiave e fallisce se la media per caso scende sotto la soglia o se lo stato non è tra quelli ammessi.
- Integrare lo script in CI come job "document-smoke-tests" per avere una verifica rapida post-deploy.

## 4. Test cross-device e di rete
- **iOS Safari:** eseguire tramite Safari/Simulator in modalità 3G/4G; validare scatto live e upload da galleria, rotazioni del device e continuità dopo perdita di rete breve (toggle modalità aereo per 5s).
- **Android Chrome:** ripetere gli stessi casi usando DevTools > *Network throttling* 3G/4G; verificare sia il flusso camera che quello di upload file.
- **Fallback upload:** scollegare i permessi camera o simulare errore hardware e confermare che il flusso ripiega sull'upload manuale mostrando messaggio esplicito e conservando i metadati nel payload.
- Registrare gli esiti in una matrice (caso × dispositivo × rete) e allegare screenshot delle schermate chiave (consenso, preview, esito OCR) per audit.

## 5. Checklist rapida
- [ ] Ogni combinazione paese/tipo ha ≥10 immagini etichettate con ground truth.
- [ ] Tutte le varianti difficili coperte (`glare`, `angled`, `shadow`, `partial_crop`).
- [ ] Smoke test verdi con accuratezza ≥ soglia e stato `VERIFIED` o `NEEDS_REVIEW` atteso.
- [ ] Test iOS Safari e Android Chrome eseguiti su reti 3G e 4G con fallback upload validato.
