# HR Portal – stato attuale e proposte di completamento

## Stato attuale (sintesi tecnica)
- **Documenti HR**: modello con targeting per ruolo/azienda/struttura, visibilità temporale e workflow di presa visione (ManyToMany `acknowledged_by`).【F:hr_portal/models.py†L14-L75】 Il frontend mostra elenco e consente la conferma di lettura via API dedicata.【F:frontend/src/modules/hr/HrPortalApp.jsx†L44-L115】【F:frontend/src/modules/hr/HrPortalApp.jsx†L363-L372】
- **Notifiche HR**: modello con categorie, scheduling, scadenza e audience filtrata; endpoint REST con azione `deliver` che invoca il servizio di recapito.【F:hr_portal/models.py†L96-L160】【F:hr_portal/views.py†L19-L66】 La UI visualizza solo la “hero notification”, senza lista né stato di recapito.【F:frontend/src/modules/hr/HrPortalApp.jsx†L344-L361】
- **Buste paga**: ingestion di batch PDF/ZIP con auto-match su username/email/regex, OCR opzionale, code di “unmatched” e log dettagliato; endpoint per segnare il download.【F:hr_portal/models.py†L200-L366】【F:frontend/src/modules/hr/HrPortalApp.jsx†L81-L116】【F:frontend/src/modules/hr/HrPortalApp.jsx†L374-L392】
- **Sportello d’ascolto**: ticket con SLA, sentiment e messaggi; la UI supporta messaggi e chiusura ticket, ma non creazione/assegnazione né filtri avanzati.【F:hr_portal/views.py†L113-L197】【F:frontend/src/modules/hr/HrPortalApp.jsx†L154-L234】【F:frontend/src/modules/hr/HrPortalApp.jsx†L394-L412】
- **Preferenze di notifica**: modello con canali e quiet hours, restituito via API e mostrato come read-only nel frontend.【F:hr_portal/models.py†L77-L94】【F:frontend/src/modules/hr/HrPortalApp.jsx†L133-L152】【F:frontend/src/modules/hr/HrPortalApp.jsx†L415-L419】

## Azioni prioritarie per completare il portale
1. **Gestione end‑to‑end delle notifiche**
   - Backend: estendere le viewset per CRUD, pubblicazione/archiviazione, filtri stato/categoria e azione di re‑invio per le consegne fallite, sfruttando `HRNotificationDelivery` e `IsHRorSuperAdmin`.【F:hr_portal/views.py†L19-L113】
   - Frontend: creare viste lista/dettaglio con form di composizione, scheduler, pulsante di re‑invio e tab di monitoraggio recapiti (successi/fallimenti) con badge di conteggio.
2. **Workflow di caricamento buste paga**
   - UI per creare/eseguire `PayslipBatch`: upload ZIP/PDF, scelta strategia match (username/email/regex), toggle OCR e lingua, con feedback del processing log.
   - Pannello “DA ASSEGNARE” per usare `PayslipUnmatched.resolve`, rigenerare nome periodo e rieseguire validazioni; aggiungere filtro/paginazione sugli unmatched.
3. **Sportello d’ascolto avanzato**
   - Consentire apertura ticket dal portale (subject/message, anonimato opzionale) e flusso di assegnazione/riassegnazione HR lato backend.
   - Filtri per stato/priorità/SLA e vista compatta “in scadenza” con badge; aggiungere reminder SLA via polling/WebSocket.
4. **Preferenze notifiche editabili**
   - Form UI per modificare canali (email/push/SMS) e quiet hours, con salvataggio su `NotificationPreference` via PUT/PATCH; convalidare le finestre silenziose lato backend.
5. **Coerenza autorizzazioni e osservabilità**
   - Allineare il frontend con `IsHRorSuperAdmin` e i vincoli azienda/struttura già applicati nelle queryset backend, evitando l’esposizione di dati cross-azienda.【F:hr_portal/views.py†L19-L197】
   - Ampliare `HREventLog` con eventi chiave (creazione/errore batch, cambio stato notifiche, assegnazioni ticket) e aggiungere un pannello di audit accessibile dal portale.
6. **UX e prestazioni**
   - Skeleton loading per sezioni lenti; paginazione e ricerca su documenti e buste paga; badge di conteggio per notifiche non lette e code unmatched.
   - Polling leggero o WebSocket per aggiornare in tempo reale notifiche, esiti di batch e ticket; throttling sulle liste più pesanti.

## Deliverable suggerito
- Iterazione 1: backend+frontend per upload batch buste paga e CRUD notifiche con re‑invio/monitoraggio.
- Iterazione 2: ticketing (creazione, assegnazioni, filtri SLA) e preferenze notifiche editabili.
- Iterazione 3: audit log, skeleton/paginazione/badge e canale realtime.
