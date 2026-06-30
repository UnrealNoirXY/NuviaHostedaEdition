# Inventario formati payroll e regole di match

## Formati attualmente gestiti in input

| Formato | Supporto attuale | Note operative |
| --- | --- | --- |
| PDF singolo (multipagina) | ✅ Sì | Il file viene letto pagina per pagina, con split in segmenti quando cambia l'identificativo o il periodo. Se il testo non contiene identificativi chiari si attiva l'OCR (se abilitato). |
| ZIP di PDF | ✅ Sì | Ogni file PDF nel ZIP è trattato come payslip separato. I file non PDF vengono saltati. |
| CSV / XML | ❌ No | Non esistono handler per CSV/XML in `PayslipBatch.process`. Eventuali integrazioni future dovranno introdurre un nuovo parser e relativa validazione. |

## Campi identificativi e priorità di match

L'auto-match usa le regole già presenti in `PayslipBatch`:

1. **Codice fiscale (CF)**
   - Ricerca tramite regex `[A-Z]{6}\d{2}[A-Z]\d{2}[A-Z]\d{3}[A-Z]` su testo e (se fallback) sul nome file.
   - Ha la priorità massima nella selezione del candidato primario.
2. **Email**
   - Riconosciuta con presenza di `@` tra i candidati.
3. **Username**
   - Usato in match diretto quando non è stato trovato CF o email.
4. **Nome + Cognome**
   - Estratti come pattern `Nome Cognome` (case-sensitive) o stringhe in maiuscolo tipo `NOME COGNOME`.
   - Usati solo se non si sta facendo match basato esclusivamente su CF.

### Strategia di match (ordine effettivo)

1. **`auto_match_strategy = fiscal_code`**
   - Match solo sui campi fiscali (`fiscal_code`, `tax_code`, `codice_fiscale` se presenti sul modello utente).
2. **`auto_match_strategy = email`**
   - Match su `email__iexact`.
3. **`auto_match_strategy = username`**
   - Match su `username`.
4. **Default**
   - Tentativo su `username`, poi `email__iexact`.
5. **Fallback nome+cognome**
   - Se le ricerche precedenti falliscono e il candidato ha esattamente due token.

## Regole definitive di normalizzazione

Le seguenti regole riflettono l'attuale pipeline di normalizzazione, con indicazione delle motivazioni operative:

1. **Trim**
   - Ogni candidato viene ripulito con `.strip()`.
2. **Compressione spazi**
   - Spazi multipli vengono ridotti a singolo spazio (`re.sub(r"\s+", " ", ...)`).
3. **Uppercase per confronto dei token**
   - I token vengono confrontati in uppercase per identificare stop words.
4. **Stop words (rumore)**
   - I candidati che contengono parole chiave di rumore (es. `SOCIETA`, `SRL`, `SPA`, `INPS`, `INAIL`, `AZIENDA`, `DIPENDENTE`) vengono scartati.
5. **Deduplica**
   - I candidati normalizzati e non rumorosi sono deduplicati mantenendo l'ordine di priorità.

## Indicazioni per integrazioni future (CSV/XML)

Per supportare CSV/XML in modo stabile si suggerisce:

- **Parsing dedicato** con mapping esplicito delle colonne/elementi a CF, email, username, nome, cognome.
- **Normalizzazione uniforme** usando le stesse regole definite sopra (trim, compressione spazi, stop words).
- **Log di diagnostica** con `identifier_source` = `csv`/`xml` per analisi batch.
- **Test di regressione** con input misti (CF assente, email non valida, nome+COGNOME in maiuscolo).
