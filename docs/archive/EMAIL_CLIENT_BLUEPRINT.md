# Blueprint Prodotto: Email Workspace Aziendale (Inbound + Outbound) con UX Semplificata

## 1) Posizionamento Strategico

### Decisione prodotto
Per questo ecosistema la scelta consigliata è **B) Email layer integrato nella piattaforma**, non clone completo di Outlook/Gmail.

Questo significa:
- esperienza tipo client completo per i bisogni core (leggere/scrivere/organizzare);
- integrazione nativa con workflow aziendali (ticket, task, booking, CRM);
- UX guidata per dipendenti non tecnici.

Ispirazione funzionale: solidità operativa stile eM Client.
Differenziazione: riduzione complessità e produttività operativa.

---

## 2) Obiettivi Prodotto
Creare un modulo email integrato che permetta agli utenti di:
- leggere e organizzare la posta in entrata;
- scrivere, rispondere, inoltrare e pianificare invii;
- gestire firme multiple e identità mittente;
- trasformare email in azioni operative con pochi click.

---

## 3) Scope Funzionale Minimo (MVP reale)

### 3.1 Posta in entrata
- Cartelle standard: Inbox, Sent, Drafts, Spam, Trash, Archive.
- Lista messaggi con stato letto/non letto, priorità, mittente, oggetto, preview.
- Ricerca veloce (mittente, oggetto, testo, allegati).
- Filtri rapidi: Non lette, Oggi, Con allegati, Da VIP.

### 3.2 Scrittura e invio
- Composer completo: Nuovo, Reply, Reply all, Forward, To/CC/BCC, allegati drag-and-drop.
- Salvataggio bozza automatico.
- Programmazione invio (send later).
- Controlli qualità pre-invio:
  - avviso allegato mancante (se testo contiene "allego" o sinonimi);
  - warning su destinatario esterno;
  - conferma su invio a liste numerose.

### 3.3 Firme e identità
- Firme multiple per utente (es. standard, commerciale, supporto).
- Placeholder dinamici: nome, ruolo, telefono, sede, disclaimer.
- Firma predefinita per account/casella.
- Editor WYSIWYG + anteprima desktop/mobile.

### 3.4 Affidabilità operativa
- Sync in background per account multipli.
- Coda invii con stato: in attesa, inviato, errore.
- Retry automatici con backoff su invio/sync falliti.

---

## 4) UX: “Semplice per tutti”

### 4.1 Layout guidato
- Sidebar minimale (cartelle + smart views).
- Lista messaggi pulita e leggibile.
- Pannello lettura con azioni principali sempre in alto.

### 4.2 Riduzione attrito
- Pulsanti fissi: Nuova email, Rispondi, Inoltra, Archivia, Segna letto/non letto.
- Niente menu profondi per azioni frequenti.

### 4.3 Composer assistito
- Template rapidi per casi ricorrenti (HR, amministrazione, supporto).
- Suggerimento oggetto se manca.
- Controllo tono opzionale (professionale/cortese/breve).

### 4.4 Accessibilità e adozione
- Scorciatoie tastiera base (R, A, F, Ctrl/Cmd+Enter).
- Contrasto elevato e font leggibili.
- Onboarding in 2 minuti con tour contestuale.

---

## 5) Architettura Tecnica (rafforzata)

### 5.1 Connessioni provider e strategia sync
Supportare due modalità:
1. OAuth/API native quando disponibili:
   - Google Workspace: Gmail API + watch/push.
   - Microsoft 365: Graph API + webhook/subscription.
2. IMAP/SMTP standard per provider generici:
   - IMAP IDLE dove supportato;
   - fallback a polling intelligente incrementale.

### 5.2 Pipeline di sincronizzazione consigliata
`sync_scheduler -> account_worker -> provider_adapter -> email_parser -> thread_engine -> database/object_storage`

Dettagli chiave:
- sync incrementale per `history_id/delta_token/UID` (mai full sync continuo);
- retry con exponential backoff;
- idempotenza su ingestione messaggi;
- dead-letter queue per errori persistenti.

### 5.3 Componenti backend
- `email_accounts`: configurazioni account, token, stato connessione.
- `email_sync`: scheduler, job ingestione, delta sync.
- `email_provider_adapters`: layer provider-specific (Google/Microsoft/IMAP).
- `email_parser`: parsing MIME, normalizzazione HTML, estrazione allegati/header.
- `thread_engine`: ricostruzione conversazioni (`Message-ID`, `In-Reply-To`, `References`).
- `email_send`: pipeline invio con queue, retry, tracking esiti.
- `email_signatures`: gestione firme/versioni/default.
- `email_security`: policy, audit, rilevazione anomalie.
- `email_actions`: bridge verso task/ticket/calendario/CRM.

### 5.4 Storage model
- Metadati email nel database relazionale/search index.
- Allegati in object storage (S3/MinIO equivalente), **non** nel DB.
- Riferimenti firmati/temporanei per download sicuro allegati.

### 5.5 Composer HTML robusto
- Editor affidabile (TipTap/ProseMirror/Quill).
- Sanitizzazione HTML severa lato backend.
- Compatibilità rendering client principali (Outlook/Gmail/Apple Mail).
- Inline CSS strategy per template/firme.

---

## 6) Sicurezza (baseline obbligatoria)
- OAuth con scope minimi (least privilege).
- Cifratura token e segreti a riposo (KMS/chiavi ruotate).
- Secret redaction nei log.
- Audit trail completo su lettura messaggi sensibili, invii, modifiche firme.
- Session hardening: timeout, device awareness, revoca sessioni.
- 2FA obbligatoria su ruoli sensibili (admin/supervisor).
- DLP base:
  - warning su dati sensibili verso esterno;
  - blocco opzionale per domini non autorizzati.

---

## 7) Innovazione utile (non gimmick)

### 7.1 Smart Inbox aziendale
- Prioritizzazione con `priority_score` basato su:
  - VIP/cliente critico;
  - urgenza lessicale;
  - ruolo mittente;
  - storico interazioni.
- Vista "Da gestire oggi" auto-generata.

### 7.2 Thread Intelligence
- Estrazione automatica di:
  - decisioni prese;
  - task assegnati;
  - deadline citate.

### 7.3 Email -> Azione automatica proposta
Dalla mail, con conferma utente:
- crea task interno;
- crea ticket supporto;
- crea reminder calendario;
- collega a cliente/pratica.

### 7.4 Zero Inbox Guidata
Ogni mail passa in un flusso semplice: Rispondi / Delega / Archivia / Pianifica.

---

## 8) KPI di successo
- Tempo medio di triage inbox (target: -30%).
- Tasso di risposta entro SLA.
- Riduzione errori invio (destinatari/allegati).
- Adozione firme standard aziendali.
- CSAT interno su usabilità (> 8/10).

---

## 9) Roadmap suggerita

### Fase 1 (4-6 settimane) – MVP robusto
- Inbound + Outbound base.
- Composer con bozze automatiche e firme multiple.
- Sync incrementale per 1-2 provider principali.
- Audit e sicurezza base.

### Fase 2 (4-8 settimane) – Produttività
- Smart Inbox.
- Template e suggerimenti scrittura.
- Send later + coda invii avanzata.
- Integrazione task/ticket/calendario.

### Fase 3 (continuo) – Enterprise hardening
- DLP avanzato.
- Regole compliance per dipartimento.
- Analytics adozione/performance + ottimizzazione costi infrastrutturali.

---

## 10) Rischi principali + mitigazioni
- **Variabilità provider email** -> adapter layer + test matrix provider.
- **Threading inconsistente** -> `thread_engine` dedicato + test su header reali.
- **Token scaduti/revoche** -> refresh robusto + UX di riconnessione guidata.
- **Carico elevato sync** -> queue scalabile, throttling, backoff e delta sync.
- **Compatibilità HTML email** -> sanitizer + suite rendering multi-client.

---

## 11) Definizione pratica di “funzionante al 100%”
Per evitare promesse non realistiche, "100%" significa:
- SLO di disponibilità e latenza rispettati;
- error budget monitorato;
- retry/fallback efficaci su failure provider;
- nessuna perdita di messaggi/bozze;
- incident response con alerting proattivo.

In breve: non "mai errori", ma "errori gestiti senza impatto utente".
