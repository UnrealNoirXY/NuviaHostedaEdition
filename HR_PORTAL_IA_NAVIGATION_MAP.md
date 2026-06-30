# Fase 0 — Allineamento obiettivi e mappa di navigazione (1 settimana)

## Output
- IA (information architecture) rivista.
- Mappa di navigazione HR.

## Macro‑aree (5)
1. **Documenti personali** (primaria)
2. **Buste paga** (secondaria)
3. **Comunicazioni** (terziaria)
4. **Sportello d’ascolto** *(solo superadmin)*
5. **Preferenze & Audit** *(solo superadmin)*

---

## 1) Documenti personali
**Scopo:** rendere immediatamente visibili i documenti personali dell’utente, con accesso rapido a ciò che richiede attenzione.

**Azioni principali già disponibili oggi**
- Visualizzare repository documenti HR.
- Aprire/Scaricare documento.
- Confermare lettura/acknowledgement documento quando previsto.

**Viste necessarie per renderle “scopribili”**
- **Dashboard HR (entry point):** card “Documenti personali” con contatore *da leggere* e *da firmare*.
- **Documenti (list):** repository con filtri essenziali (es. “Tutti”, “Da leggere”, “Da firmare”), badge stato.
- **Documento (detail):** preview o download + CTA di conferma lettura/firma.

---

## 2) Buste paga
**Scopo:** accesso rapido alle buste paga individuali e visibilità per HR sulle assegnazioni.

**Azioni principali già disponibili oggi**
- Visualizzare elenco buste paga assegnate all’utente.
- Scaricare busta paga.
- Tracciamento download (audit già presente).
- Per HR: visualizzare batch caricati e stato (completato / da assegnare).
- Per HR: risolvere buste paga non abbinate (coda “DA ASSEGNARE”).

**Viste necessarie per renderle “scopribili”**
- **Dashboard HR/Utente (entry point):** card “Buste paga” con ultimo periodo disponibile.
- **Buste paga (list utente):** lista per periodo con stato download.
- **Busta paga (detail):** dati essenziali + download.
- **Batch HR (list):** vista stato batch con contatori (assegnate/da assegnare).
- **Coda “DA ASSEGNARE” (detail):** dettaglio item con azione di risoluzione.

---

## 3) Comunicazioni
**Scopo:** rendere immediatamente visibili comunicazioni HR e notifiche operative.

**Azioni principali già disponibili oggi**
- Visualizzare elenco notifiche con stato (letto/non letto).
- Aprire dettaglio notifica.
- Confermare lettura/acknowledgement per comunicazioni che lo richiedono.

**Viste necessarie per renderle “scopribili”**
- **Dashboard HR (entry point):** card “Comunicazioni” con contatore *non lette* e *da confermare*.
- **Notifiche (list):** lista con filtri base (tutte / non lette / da confermare), badge stato.
- **Notifica (detail):** contenuto completo + CTA di conferma lettura.

---

## 4) Sportello d’ascolto (solo superadmin)
**Scopo:** accesso rapido alle richieste già gestite dal sistema (backend già presente).

**Azioni principali già disponibili oggi**
- Visualizzare elenco ticket.
- Aprire dettaglio ticket con timeline messaggi.
- Inviare messaggi (interni/utente).
- Chiudere ticket.

**Viste necessarie per renderle “scopribili”**
- **Dashboard HR (entry point):** card “Sportello d’ascolto” con contatore ticket aperti.
- **Ticket (list):** lista con filtri essenziali (aperti/chiusi).
- **Ticket (detail):** timeline conversazione + azioni chiusura.

---

## 5) Preferenze & Audit (solo superadmin)
**Scopo:** rendere evidenti le impostazioni di canale e la tracciabilità delle azioni.

**Azioni principali già disponibili oggi**
- Gestire preferenze canale (in‑app/email/push) e quiet hours.
- Consultare log/audit eventi (creazione, lettura, download, ACK).

**Viste necessarie per renderle “scopribili”**
- **Dashboard HR (entry point):** card “Preferenze” + entry “Audit”.
- **Preferenze (form):** pannello di configurazione canali e quiet hours.
- **Audit (list):** timeline eventi con filtri base (tipo evento / periodo).

---

## Regole di visibilità (superadmin vs non-superadmin)
- **Utente non superadmin:** vede solo Documenti personali, Buste paga, Comunicazioni.
- **Superadmin:** vede anche Sportello d’ascolto e Preferenze & Audit.
- **API evitate per non-superadmin:** `/api/hr/notification-preferences/` e `/api/hr/listening-tickets/`.

## Mappa di navigazione HR (sintesi)
- **Dashboard HR**
  - Documenti personali
    - Documenti → Dettaglio documento
  - Buste paga
    - Elenco buste paga (utente)
    - Batch HR → Coda “DA ASSEGNARE” → Dettaglio item
  - Comunicazioni
    - Notifiche → Dettaglio notifica
  - Sportello d’ascolto *(solo superadmin)*
    - Ticket → Dettaglio ticket
  - Preferenze & Audit *(solo superadmin)*
    - Preferenze canali/quiet hours
    - Audit eventi
