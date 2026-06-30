# Piano Operativo per Suite HR Integrata

## 1. Obiettivi e principi guida
- Deliverable: strumento HR unico per notifiche, documenti e buste paga con split automatico, coerente con identità visiva degli altri strumenti.
- Vincoli: nessuna regressione sull'ecosistema esistente; rispetto rigoroso dei permessi per account/società/strutture; il superamministratore mantiene visibilità totale e privilegi di override/audit.
- Qualità: esperienza moderna e reattiva (mobile-first), con storytelling e componenti riutilizzabili per preservare uniformità grafica.

## 2. Architettura e governance dei permessi
- Frontend: SPA React/Vite con design tokens e componenti condivisi (palette, tipografia, spacing) già adottati dagli altri moduli; layout modulare (cards/panels) per integrazione nella dashboard esistente senza scostamenti visivi.
- Backend: servizi Django REST modulati in tre domini (notifiche-documenti, payroll ingestion, sportello) con API versionate e feature flag per rollout graduale senza regressioni.
- Permessi multi-tenant: matrice Ruolo × Società × Struttura; il superamministratore bypassa i filtri ma opera sempre con audit trail; HR admin può gestire solo entità del proprio perimetro; i dipendenti vedono solo risorse loro o delle strutture associate.
- Storage sicuro: bucket separati per documenti HR e buste paga cifrate; chiavi KMS per file at-rest; link firmati a tempo per il download.

## 3. Notifiche e documenti (workflow end-to-end)
- Pubblicazione guidata: wizard HR per creare notifiche/documenti con visibilità per ruolo/gruppo/società/struttura, finestra temporale e necessità di acknowledgement.
- Tracciabilità: audit per ogni evento (creazione, update, lettura, ACK); dashboard di letture per HR e superamministratore con filtri per account/società.
- UX coerente: card notifiche e repository documenti condividono i pattern di listing, breadcrumb e filtri già in uso sugli altri strumenti; quick actions inline (download, assegna, richiedi firma).
- Preferenze utente: canali opt-in (in-app, email, push) e quiet hours; template di messaggistica riutilizzabili con variabili (nome, struttura, periodo paga).

## 4. Pipeline buste paga con split e assegnazione automatica
- Input supportati: PDF multi-busta o ZIP; metadati configurabili (regex su CF/ID, QR/barcode, manifest XML/CSV) per riconciliare dipendenti.
- Flusso batch: upload in area staging, validazione schema, split per dipendente, cifratura per bucket payroll, assegnazione all'account corretto via lookup anagrafica (account/società/struttura) con fallback a coda di revisione manuale.
- Automazione notifiche: al termine, generazione notifica con link firmato per ogni dipendente; retry con backoff se delivery fallisce; report di esito per HR e superamministratore.
- Gestione errori e regressioni: record orfani in coda "resolve" (UI per abbinare manualmente); metriche (tempo medio split, error rate, percentuale auto-match) per monitorare impatti e prevenire regressioni.

## 5. Sportello d'ascolto digitale (deprecato)
- Il modulo non viene utilizzato: rimuovere la sezione dal portale HR mantenendo intatti i modelli e le API per compatibilità, visibili solo da backend/admin.

## 6. Sicurezza, osservabilità e qualità
- Sicurezza: cifratura in transito; 2FA/SSO; policy di retention differenziata (documenti, buste paga, ticket); controllo versione documenti e revoca accessi immediata per cambi ruolo.
- Observability: log strutturati per ogni API, tracing per pipeline di split, metriche (p95 latency, ACK rate, tasso auto-match) con alerting; dashboard di salute per prevenire regressioni.
- Qualità: test unit e integration (mock storage, KMS, code split), E2E per flussi chiave (upload buste, ACK notifica, apertura ticket); canary release con feature flag e rollback automatico.

## 7. Roadmap incrementale (senza regressioni)
- Sprint 1: setup permessi/matrice accessi, skeleton API v1 e shell UI coerente; storage separato e audit base.
- Sprint 2: wizard notifiche/documenti, ingest pipeline buste paga con auto-match >70%, dashboard letture e revisione manuale.
- Sprint 3: completamento osservabilità e canary per validare l'assenza di regressioni prima del rollout totale (senza sportello d'ascolto UI).

## 8. Implementazione iniziale (questa iterazione)
- Nuovo modulo **hr_portal** in Django con modelli per documenti HR, batch di buste paga con auto-match da ZIP/PDF e ticket di sportello d'ascolto.
- API REST `api/hr/` con viewset per documenti HR, batch di buste paga, buste paga utente e ticket di ascolto, protette da permessi HR/superadmin e scoping multi-company/resort.
- Pipeline di processamento batch che legge archivi ZIP di PDF, tenta il match automatico su username/email (o regex configurabile) e genera log/metriche di assegnazione.
- Endpoint di acknowledgement documenti per tracciare chi ha letto/accettato e azione di ri-processamento dei batch buste paga con log più robusti e validazione regex del manifest.
- Endpoint per segnare il download della busta paga con tracciamento `downloaded_at` e visibilità HR limitata al proprio perimetro (società/struttura), mantenendo il superamministratore con accesso completo.
- Coda di revisione manuale per buste paga non abbinate: gli item orfani vengono salvati come `PayslipUnmatched` con file originale e possono essere assegnati via API dedicata (`/api/hr/payslip-unmatched/<id>/resolve/`), aggiornando automaticamente i contatori del batch e preservando i vincoli di perimetro HR.
- Ingest da PDF unico multi-busta: il batch accetta anche un PDF unico, divide le pagine in PDF singoli, estrae testo per intercettare codice fiscale/nome con regex configurabile e tenta l’assegnazione automatica; gli item senza match finiscono in coda con stato visibile “DA ASSEGNARE”.
- OCR opzionale sulle pagine PDF quando il testo embedded non contiene identificativi chiari: viene generata un'immagine via pypdfium2 e passata a Tesseract (lingue configurabili, default ita+eng) per cercare nome, cognome e codice fiscale prima di considerare un item come da assegnare.
- Metriche e audit trail: i batch calcolano durata di processamento e tasso di auto-match, mentre un registro `HREventLog` traccia ACK documenti, download/assegnazioni buste paga e azioni sullo sportello con scoping company/resort.
- Sportello d’ascolto con SLA: mantenere solo backend/admin per consultazione e audit, rimuovere la UI dal portale.
- Notifiche HR modulari: modello per stato (bozza/pubblicata/archiviata), target per ruolo/company/resort e scadenza; preferenze per canali (email/push/SMS) e quiet hours per utente.
- Delivery canale-aware: tabella di `HRNotificationDelivery` per tracciare email/push/SMS consegnate o fallite, endpoint/API/admin per consultare le consegne e azione `deliver` che applica audience e preferenze utente.
- Automazioni post-busta paga: ogni busta paga auto-assegnata o risolta genera un tentativo di email all’utente (rispettando quiet hours/preferenze) e logga l’esito; comando `deliver_hr_notifications` consente il recap periodico delle notifiche pianificate.
- Conversazioni ticket: timeline di messaggi (interni e visibili all’utente) collegati ai ticket con logging automatico degli eventi.
- Osservabilità incrementale: middleware di log strutturati e metriche in-memory per latenza HTTP e consegna notifiche, con snapshot esportabile e logging JSON-ready per integrazione futura con APM/alerting.
- Shell UI React/Vite: cruscotto HR coerente con il design esistente per documenti (ACK), buste paga con download tracking e coda "DA ASSEGNARE", notifiche utente e sportello d'ascolto con timeline conversazionale e chiusura ticket.

## 9. Rimodulazione piano (task per Codex)
### Obiettivo
- Nascondere **Logs** dal portale HR (visualizzazione esclusiva nel pannello Django admin).
- Rimuovere dal portale HR le sezioni **Sportello d’ascolto** e **Composizione e scheduling** (non utilizzate).
- Mantenere **immutate** le funzionalità backend e i permessi esistenti.

### Task list operativa (formato Codex)
**Fase 1 — Avvio intervento (iniziare da qui)**

**Task 1 — Audit UI attuale**
- **File target**: `frontend/src/modules/hr/HrPortalApp.jsx`
- **Cosa fare**: individuare le sezioni:
  - “Logs/Audit” (lista eventi) da nascondere.
  - “Sportello d’ascolto” (ticket + messaggi) da rimuovere.
  - “Composizione e scheduling” (form nuova notifica) da rimuovere.
- **Output**: lista delle porzioni di UI da eliminare e chiamate API collegate.

**Task 2 — Rimozione Sportello d’ascolto**
- **File target**: `frontend/src/modules/hr/HrPortalApp.jsx`
- **Cosa fare**:
  - eliminare sezione UI e chiamate API (load ticket, invio messaggi, chiusura ticket);
  - rimuovere CTA/link legati ai ticket;
  - rimuovere badge/contatori legati ai ticket.
- **Output**: sportello non visibile nel portale, backend invariato.

**Task 3 — Rimozione “Composizione e scheduling”**
- **File target**: `frontend/src/modules/hr/HrPortalApp.jsx`
- **Cosa fare**:
  - eliminare il form di creazione/scheduling notifiche;
  - rimuovere pulsanti/CTA legate alla composizione;
  - mantenere sola visualizzazione read-only delle notifiche.
- **Output**: UI notifiche solo in lettura.

**Task 4 — Nascondere Logs**
- **File target**: `frontend/src/modules/hr/HrPortalApp.jsx`
- **Cosa fare**:
  - rimuovere/occultare sezione “Logs/Audit” dal portale;
  - nessuna modifica backend (log consultabili da Django admin).
- **Output**: Logs visibili solo in admin.

**Task 5 — Allineamento UI e layout**
- **File target**: `frontend/src/hr-portal.css` (solo se necessario)
- **Cosa fare**:
  - aggiornare griglie/spaziature dopo la rimozione sezioni;
  - rivedere testi/etichette che citano sezioni eliminate.
- **Output**: layout pulito senza vuoti.

**Task 6 — Verifica finale**
- **Cosa fare**:
  - aprire portale HR con utente HR;
  - verificare assenza di Sportello, Composizione/Scheduling e Logs;
  - verificare presenza e funzionamento di Documenti, Notifiche user, Buste paga.
- **Output**: smoke test manuale superato.

### Output atteso
- Portale HR più snello: solo **Documenti**, **Notifiche utente**, **Buste paga** e preferenze visibili.
- Accesso ai **Logs** solo da Django admin.
- Nessuna modifica a modelli, API o permessi.
