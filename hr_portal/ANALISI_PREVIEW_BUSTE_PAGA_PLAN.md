# Analisi approfondita: strumento divisione buste paga con preview

## Obiettivo dell’analisi
Valutare perché la feature preview/split buste paga risulti “inutilizzabile” dal punto di vista operativo e definire un piano realistico per renderla affidabile, comprensibile e utile in produzione.

---

## 1) Stato attuale: cosa esiste davvero oggi

### 1.1 Backend preview: c’è una pipeline completa (ma con punti fragili)
- Esiste un endpoint per avvio preview (`preview-start`) che crea un job asincrono.
- Esiste un endpoint SSE (`preview-stream/<token>`) che pubblica progress e payload preview.
- Esiste un endpoint polling (`preview-status/<token>`) per leggere lo stato job.
- Il job processa PDF/ZIP, produce segmenti, prova auto-match, raccoglie eventi e può salvare immagini di pagine (`scan_pages`) se disponibile rendering PDF.
- È previsto il “lock/conferma preview” con token (`preview-confirm`) usato poi in creazione batch.

### 1.2 Frontend preview: molta UX “simulata”, poca evidenza reale
- La UI presenta un’area “Anteprima in tempo reale” ricca di badge/indicatori.
- Vengono mostrati segmenti, match score, testo estratto e comandi di assegnazione manuale.
- Tuttavia la preview visiva pagine è solo grafica placeholder (scanline/cards), non una vera resa delle pagine PDF.
- Le immagini reali eventuali (`scan_pages`) vengono lette nello state ma non sono rese in UI.

### 1.3 Processo business
- Dopo la conferma preview, la creazione batch usa il token preview per riapplicare assegnazioni manuali.
- La creazione batch avvia anche la processazione reale.

**Sintesi:** il sistema non è “vuoto”, ma l’esperienza percepita dall’utente può sembrare non funzionante perché l’elemento più atteso (preview visuale concreta) non è effettivamente mostrato.

---

## 2) Root cause analysis (perché “non fa vedere preview” e “non fa niente”)

## A. Gap principale UX/funzionale: preview visiva non renderizzata
**Impatto:** Altissimo.
- Backend produce `scan_pages` con `image_url` quando possibile.
- Frontend non usa `scanPages` in rendering: l’utente non vede “anteprima reale” delle pagine, solo card/testo/placeholder.
- Questo da solo può spiegare la percezione “non funziona”.

## B. Dipendenza forte da SSE per la UX live
**Impatto:** Alto.
- La UI si basa su `EventSource` per aggiornare progress e payload.
- Se SSE è bloccata da proxy/reverse proxy, timeout, buffering, auth/sessione o CORS/cookie, l’utente ottiene errore di connessione e la preview si interrompe.
- C’è endpoint polling disponibile ma non usato come fallback automatico di prodotto.

## C. Asincronia in-process (thread locale) non robusta in produzione
**Impatto:** Alto.
- Il job preview parte con thread daemon nel processo web.
- In ambienti multi-worker/redeploy/riavvio, questa scelta può interrompere job o renderne il comportamento non deterministico.
- Manca una coda job dedicata e osservabilità specifica di “job health”.

## D. Dipendenze OCR/rendering opzionali non governate da capability chiare
**Impatto:** Medio-Alto.
- OCR/rendering dipendono da librerie opzionali (es. pypdfium2).
- Se non presenti, la preview degrada ma l’utente non sempre percepisce chiaramente cosa è disponibile e cosa no.

## E. Visibilità errori insufficiente per operatore
**Impatto:** Medio.
- Errori tecnici vengono mostrati in banner sintetico, ma senza troubleshooting guidato.
- Manca una diagnostica esplicita: “SSE non disponibile, sto passando a polling”, “OCR non attivo perché dipendenza mancante”, “segmentazione vuota perché PDF senza testo”.

## F. Mismatch tra promessa UI e valore operativo
**Impatto:** Medio.
- UI molto ricca (badge, stati, carte animate) ma senza preview visuale reale “first class”.
- Per un tool di divisione buste paga, l’operatore si aspetta conferma visuale per pagina/segmento.

---

## 3) Obiettivo target (definizione di “strumento ottimizzato e funzionale”)

Lo strumento è considerato “funzionante” quando:
1. L’utente vede sempre una preview utilizzabile (immagine pagina o alternativa chiara).
2. La preview continua a funzionare anche se SSE fallisce (fallback automatico polling).
3. La creazione batch è coerente al 100% con la preview confermata.
4. Gli errori sono espliciti e azionabili.
5. Le performance sono prevedibili su file reali (PDF singolo e ZIP multipli).

---

## 4) Piano dettagliato di rilancio (priorità + deliverable)

## Fase 0 (1-2 giorni) – Stabilizzazione immediata “salvavita”

### 0.1 Mostrare davvero le pagine preview
- Rendere in UI le immagini da `preview.scan_pages` (thumbnail cliccabili).
- Associare visivamente pagina ↔ segmento (es. badge pagina iniziale/finale).
- Fallback UI se immagini assenti: messaggio esplicito “Anteprima grafica non disponibile, uso testo estratto”.

### 0.2 Fallback automatico da SSE a polling
- Se SSE va in errore, avviare polling su `preview-status/<token>` ogni 1-2s.
- Mantenere stesso state object (`progress`, `status`, `preview`, `error`).
- Mostrare banner “Connessione live non disponibile, aggiornamento automatico in polling”.

### 0.3 Messaggi operativi chiari
- Error taxonomy in frontend:
  - errore autenticazione stream,
  - errore parsing payload,
  - OCR non disponibile,
  - file non supportato,
  - preview vuota.

**Exit criteria fase 0**
- L’utente vede contenuto preview reale nel 90%+ dei PDF processabili.
- Nessun caso in cui SSE bloccata = preview inutilizzabile.

---

## Fase 1 (3-5 giorni) – Robustezza backend e consistenza di processo

### 1.1 Spostare job preview su coda dedicata
- Sostituire thread daemon con task queue (es. Celery/RQ).
- Salvare stato job in DB come già fatto, ma eseguito da worker separato.
- Retry policy e timeout controllati.

### 1.2 Contratto API preview versionato
- Definire schema stabile di payload preview (`preview_type`, `segments`, `scan_pages`, `events`, `capabilities`).
- Aggiungere campo `capabilities` con flag espliciti (`rendering_available`, `ocr_available`, `stream_available`).

### 1.3 Coerenza preview -> process reale
- Test end-to-end: le assegnazioni confermate in preview devono risultare identiche nel batch finale.
- Validare period label e segment key con errori puntuali per riga/segmento.

**Exit criteria fase 1**
- Job preview affidabili su restart/redeploy.
- Zero divergenze note tra preview confermata e batch finale.

---

## Fase 2 (4-6 giorni) – Qualità operativa e UX HR

### 2.1 Pannello “Da verificare” centrato su lavoro HR
- Vista filtrata segmenti non matchati/non confermati.
- Azioni bulk robuste (assegna tutti, applica periodo, reset selettivo).

### 2.2 Evidenza confidenza matching
- Esplicitare score e fonte identificazione (testo vs filename).
- Evidenziare mismatch ad alto rischio (score basso, testo mancante, OCR fallback).

### 2.3 Controlli pre-submit batch
- Checklist finale:
  - segmenti senza destinatario,
  - periodi invalidi,
  - errori di estrazione.
- Blocco submit opzionale “strict mode”.

**Exit criteria fase 2**
- Riduzione significativa dei segmenti lasciati senza assegnazione.
- Riduzione errori post-process e ticket HR di correzione.

---

## Fase 3 (2-4 giorni) – Osservabilità e KPI di prodotto

### 3.1 KPI specifici preview
- Preview success rate.
- SSE failure rate + fallback activation rate.
- Tempo medio a preview completata.
- % segmenti auto-match vs manual.
- % batch creati dopo preview confermata.

### 3.2 Tracciamento eventi operativi
- Eventi dedicati: `preview_started`, `preview_completed`, `preview_failed`, `preview_fallback_polling`, `preview_confirmed`.
- Dashboard per HR lead / owner tecnico.

### 3.3 Playbook incidenti
- Runbook con check rapidi: storage media, worker alive, dipendenze OCR/rendering, reverse proxy SSE.

**Exit criteria fase 3**
- Incident response < 30 min.
- Evidenza dati su dove il flusso si rompe.

---

## 5) Backlog tecnico prioritizzato (P0/P1/P2)

## P0 (immediato)
1. Render `scan_pages` nel frontend.
2. Fallback SSE→polling automatico.
3. Messaggi errore/diagnostica utente migliori.
4. Test frontend per stati preview (running/completed/failed/fallback).

## P1 (subito dopo)
1. Job queue esterna (non thread in-process).
2. Schema payload preview stabilizzato con capability flags.
3. Test integrazione preview-confirm-create batch.

## P2 (ottimizzazione)
1. UX “review first” per segmenti critici.
2. KPI e dashboard.
3. Runbook operativo.

---

## 6) Piano test dettagliato (da introdurre con il rilancio)

### Test funzionali backend
- PDF con testo nativo -> segmentazione + match.
- PDF immagine -> OCR disponibile/non disponibile.
- ZIP misto (PDF + file non PDF) -> summary coerente.
- Manual assignments validi/invalidi -> validazione corretta.
- Preview confirm token -> riuso su create batch.

### Test funzionali frontend
- Preview live via SSE.
- SSE error -> fallback polling.
- Rendering scan pages.
- Lock/unlock preview e modifica assegnazioni.
- Banner errori specifici.

### Test non funzionali
- File grandi (es. 200+ pagine).
- Concorrenza multiutente.
- Robustezza su restart worker.

---

## 7) Rischi e mitigazioni
- **Rischio:** integrazione coda job richiede setup infra.  
  **Mitigazione:** rollout progressivo (prima fallback polling + UI rendering).
- **Rischio:** rendering immagini aumenta storage/media.  
  **Mitigazione:** retention policy (TTL preview pages 24-72h).
- **Rischio:** payload preview cresce troppo.  
  **Mitigazione:** limitare scan pages e sample size, paginazione lato API.

---

## 8) Timeline consigliata (realistica)
- **Settimana 1:** Fase 0 completa (P0).
- **Settimana 2:** Fase 1 (queue + coerenza processo).
- **Settimana 3:** Fase 2 + avvio KPI Fase 3.

---

## 9) Definizione di successo (Go/No-Go)
- Preview visuale disponibile e leggibile.
- Fallback automatico sempre attivo in assenza SSE.
- Job preview affidabili (niente perdita su restart).
- Riduzione ticket “non vedo anteprima / non funziona”.
- Flusso HR completo: upload -> review -> conferma -> batch senza ambiguità.

