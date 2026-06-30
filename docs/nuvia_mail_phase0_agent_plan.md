# Nuvia Mail — Piano Ultra Dettagliato (Fase 0)

## 1. Obiettivo della Fase 0
Implementare una **integrazione iniziale senza regressioni** che:
- presenti Nuvia Mail come strumento opzionale;
- guidi l'utente alla configurazione della propria casella aziendale (IMAP/SMTP/OAuth);
- introduca UX mobile-first e onboarding progressivo;
- prepari il terreno tecnico per la Fase 1 (connessione reale account e sincronizzazione).

## 2. Vincoli non negoziabili
1. Nessun blocco sugli altri strumenti della suite.
2. Nessuna modifica distruttiva a permessi/ruoli esistenti.
3. Feature flag-ready per rollout graduale.
4. UI responsive, touch-friendly e accessibile.
5. Logging minimale (eventi onboarding) senza dati sensibili.

## 3. Deliverable Fase 0 (codice)
- Route dedicata: `core:nuvia_mail`.
- Pagina landing onboarding:
  - value proposition chiara;
  - checklist dati necessari;
  - procedura guidata a step;
  - callout esplicito "uso opzionale".
- Entrypoint nel menu laterale e nell'hub strumenti.
- Asset frontend dedicati:
  - `static/css/nuvia-mail.css`
  - `static/js/nuvia-mail.js`

## 4. UX Requirement dettagliati
### 4.1 Struttura contenuti
1. Hero con promessa chiara: “posta aziendale in app, senza obbligo”.
2. Card onboarding rapida (tempo setup, prerequisiti, supporto IT).
3. Setup wizard in 4 step:
   - scelta provider;
   - parametri connessione;
   - test connessione;
   - firma/preferenze.
4. Sezione “cosa ti serve” con checklist operativa.

### 4.2 Regole mobile-first
- CTA principali entro zona facile da toccare.
- Tipografia leggibile (>16px equivalente su mobile).
- Card con spaziatura ampia e target touch >44px.
- Nessun overflow orizzontale.

### 4.3 Copywriting
- Linguaggio semplice, non tecnico.
- Termini tecnici sempre accompagnati da micro-spiegazione.
- Stato “opzionale” ripetuto in 2 punti della UI.

## 5. Piano Tecnico Fase 0→1
### 5.1 Backend (prossimo step)
1. Nuovi modelli (bozza):
   - `MailAccount`
   - `MailSignature`
   - `MailOnboardingEvent`
2. Campi minimi account:
   - user FK, provider, email, imap_host/port, smtp_host/port,
   - auth_mode (oauth/password/app_password),
   - is_active, last_test_status, last_test_at.
3. Endpoint futuri:
   - `POST /api/nuvia-mail/accounts/test-connection/`
   - `POST /api/nuvia-mail/accounts/`
   - `GET /api/nuvia-mail/providers/presets/`

### 5.2 Sicurezza
- Cifratura credenziali/tokens lato server.
- Redazione segreti nei log.
- Rate limit sui test connessione.
- Audit eventi: create/update/test account.

### 5.3 Osservabilità
- Metriche onboarding:
  - visite landing
  - step completati
  - test connessione success/fail
  - setup completati

## 6. Piano QA anti-regressione
1. Smoke test login/logout.
2. Smoke test hub + sidebar su desktop/mobile.
3. Navigazione rapida su 3 strumenti critici (IT, HR, Maintenance).
4. Verifica che l'apertura pagina Nuvia Mail non modifichi sessione/perms.
5. Test responsive su viewport: 360x800, 390x844, 768x1024, 1366x768.

## 7. Definizione Done Fase 0
- [ ] Pagina Nuvia Mail accessibile da utenti autenticati.
- [ ] Onboarding visibile e comprensibile in meno di 60 secondi.
- [ ] UI mobile-first valida senza overflow.
- [ ] Nessuna regressione nei flussi principali.
- [ ] Documentazione tecnica aggiornata per Fase 1.

## 8. Backlog ordinato Fase 1
1. Preset provider (Gmail/Microsoft/Generic IMAP).
2. Test connessione reale IMAP/SMTP.
3. Salvataggio account cifrato.
4. Gestione firma base.
5. Prima inbox read-only (20 messaggi recenti).

## 9. Rischi + mitigazioni
- Config provider incompleta -> preset + validazione client/server.
- Errori credenziali -> messaggi human-readable e retry guidato.
- Complessità UX -> progressive disclosure + testi assistiti.
- Debito tecnico sync -> separare già da ora onboarding e motore sync.
