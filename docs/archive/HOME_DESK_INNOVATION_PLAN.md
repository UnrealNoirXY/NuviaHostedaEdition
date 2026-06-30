# Blueprint per una Home Desk Innovativa e al 100% Funzionante

## 1. Executive Summary
La Home Desk possiede già una base tecnologica moderna: layout responsive con `react-grid-layout`, preferenze utente salvate lato backend, e un assistente operazionale che prefigura automazioni contestuali.【F:frontend/src/main.jsx†L200-L369】【F:frontend/src/components/Dashboard.jsx†L1-L70】 Tuttavia, solo una parte del catalogo widget è realmente implementata, molte metriche mostrate sono statiche e diverse interazioni chiave (timeline, inbox operativa, focus mode) non sono collegate a dati reali. Il risultato è un'esperienza che appare innovativa a livello visivo ma non restituisce ancora informazioni affidabili per ogni ruolo.【F:frontend/src/components/WidgetRenderer.jsx†L1-L28】【F:desk/widget_config.py†L1-L107】 Questo documento analizza lo stato corrente e propone un piano di intervento per raggiungere una Home Desk realmente "mission critical".

## 2. Analisi dello Stato Attuale
### 2.1 Copertura funzionale dei widget
- Il `WidgetRenderer` risolve solo sette widget su oltre venti previsti dal registro, restituendo un placeholder generico per tutti gli altri. Ciò lascia vuote intere scrivanie di ruolo e spiega la percezione di una Home Desk "non funzionante".【F:frontend/src/components/WidgetRenderer.jsx†L1-L28】【F:desk/widget_config.py†L1-L107】
- Le API già esistenti coprono solo una parte delle esigenze (annunci, centro notifiche, attività recenti, calendario, ticket manutentori, recensioni). Mancano endpoint per KPI direzionali, analisi competitor, stock critici, ecc.【F:desk/api.py†L33-L204】
- Due versioni del widget annunci coesistono (`components/AnnouncementsWidget.jsx` e `widgets/AnnouncementsWidget.jsx`) con URL API differenti (`/api/desk` vs `/desk/api`), indice di una migrazione incompleta che può portare a inconsistenze e CORS error.【F:frontend/src/components/AnnouncementsWidget.jsx†L1-L44】【F:frontend/src/widgets/AnnouncementsWidget.jsx†L1-L46】

### 2.2 Esperienza utente e storytelling operativo
- L'hero, i controlli rapidi e la timeline trasmettono una narrativa moderna ma attingono da valori fittizi (conteggi inbox e timeline generata in memoria), quindi non reagiscono alle attività reali dell'utente.【F:frontend/src/main.jsx†L294-L680】
- La "Focus Mode" evidenzia i primi tre widget della griglia ma manca una logica che definisca dinamicamente i KPI critici o sincronizzi i filtri dei widget con il periodo selezionato.【F:frontend/src/components/Dashboard.jsx†L23-L67】【F:frontend/src/main.jsx†L294-L369】
- L'assistente manutenzione salva un draft in `sessionStorage` e reindirizza al form, ma non verifica la presenza di workflow lato backend (es. creazione ticket precompilato) né offre feedback post-azione.【F:frontend/src/main.jsx†L70-L211】

### 2.3 Affidabilità dati e governance
- Il layout viene generato automaticamente in base a `ROLE_WIDGET_MAP`, ma l'assenza dei widget implementati per molti ruoli porta a schede vuote. Un fallback intelligente (es. suggerire widget alternativi) non è ancora presente.【F:desk/api.py†L205-L280】【F:desk/widget_config.py†L55-L107】
- Non esiste un sistema di telemetria per capire quali widget vengono usati o se il salvataggio del layout fallisce. L'errore viene mostrato ma non tracciato per interventi di supporto.【F:frontend/src/main.jsx†L279-L458】

## 3. Linee Guida per Miglioramenti Strategici
### 3.1 Completare l'ecosistema widget
1. **Implementazione per ruolo**: priorizzare Director, Head Maintainer, Receptionist e Owner. Per ciascuno creare sia componente React sia API (Django REST) con caching e fallback quando i dati non sono disponibili. Garantire uniformità negli identificativi (`id` in `WIDGET_REGISTRY`) per evitare mismatch.【F:desk/widget_config.py†L1-L107】
2. **Widget dinamici**: sostituire contenuti statici con dati misurabili.
   - Inbox e timeline devono aggregare eventi reali (ticket, ordini, notifiche) sfruttando l'attuale `RecentActivityDataView` come modello e introducendo un endpoint dedicato per la timeline.【F:desk/api.py†L133-L204】
   - La Focus Mode deve attingere a metadati dei widget (es. flag `priority`) per decidere cosa evidenziare, invece di affidarsi all'ordine nel layout.【F:frontend/src/components/Dashboard.jsx†L23-L47】
3. **Configurazioni contestuali**: arricchire `WIDGET_REGISTRY` con schema di configurazione (campi, API, permessi) e presentarlo nella Widget Gallery, permettendo all'utente di personalizzare parametri come periodo, resort, metriche chiave.【F:frontend/src/components/WidgetGallery.jsx†L1-L65】

### 3.2 Innovazione UX e automazioni
1. **Timeline intelligente**: trasformare gli eventi generati in memoria in un flusso real-time usando WebSocket/Server-Sent Events, mostrando azioni suggerite (es. "Assegna ticket" direttamente dalla timeline).【F:frontend/src/main.jsx†L312-L369】【F:frontend/src/main.jsx†L600-L678】
2. **Assistente proattivo**: collegare il wizard di manutenzione con un'API che crea una bozza ticket e restituisce ID e stato, consentendo alla Home Desk di mostrare immediatamente l'avanzamento e permettere di allegare media dal widget stesso.【F:frontend/src/main.jsx†L70-L211】
3. **Focus Mode semantica**: aggiungere un livello di intelligenza che misura il livello di rischio di ogni widget (es. KPI fuori soglia) e aggiorna dinamicamente hero, inbox e colori. Includere notifiche push quando la modalità focus viene attivata automaticamente (soglia superata).
4. **Onboarding e suggerimenti**: integrare micro-tour e badge di completamento per spiegare nuove funzionalità, registrando progressi nell'API delle preferenze utente.【F:frontend/src/main.jsx†L469-L678】

### 3.3 Affidabilità operativa e qualità dati
1. **Contratti API consistenti**: consolidare i percorsi `/api/desk/...` e `/desk/api/...`, deprecare i duplicati e introdurre versionamento (`/api/desk/v1`). Aggiornare i client per usare un unico `apiClient` così da gestire errori e retry in modo centralizzato.【F:frontend/src/components/AnnouncementsWidget.jsx†L1-L44】【F:frontend/src/widgets/AnnouncementsWidget.jsx†L1-L46】
2. **Osservabilità**: strumentare logging strutturato lato backend per ciascun widget, con metriche (tempo risposta, numero record) e tracing degli errori di salvataggio layout o fetch dati.【F:frontend/src/main.jsx†L226-L291】【F:desk/api.py†L205-L280】
3. **Test end-to-end**: automatizzare scenari Cypress/Playwright per layout drag&drop, aggiunta widget, focus mode, risposta inviti, e wizard manutenzione. Collegare gli E2E alla pipeline di deploy per assicurare regressioni zero prima di rilasci.
4. **Accessibilità e performance**: verificare ARIA roles già presenti e completare con skip links, focus trap nelle modali (Widget Gallery, Assistente). Ottimizzare il bundle dinamicamente caricando i widget "pesanti" tramite `React.lazy`/code splitting.

## 4. Roadmap di Implementazione
1. **Fase Alpha (2 settimane)**
   - Bonifica delle API (unificazione endpoint, aggiunta metriche di logging).
   - Implementazione widget critici per Director e Head Maintainer con dati reali.
   - Aggancio timeline/inbox ai nuovi endpoint.
2. **Fase Beta (3 settimane)**
   - Estensione widget per Receptionist, Owner, Housekeeping e area Economato.
   - Introduzione Focus Mode semantica e filtri timescale coerenti (propagazione ai widget via context/provider).
   - Bozza API per assistente manutenzione + telemetria layout.
3. **Fase GA (3 settimane)**
   - Rilascio automazioni push (WebSocket), onboarding guidato e test E2E completi.
   - Introduzione configurazioni avanzate widget e code splitting.
   - Monitoraggio continuo con dashboard analytics interna (es. mixpanel-like) per adoption rate.

## 5. KPI di Successo
- **Copertura widget**: ≥ 95% dei widget del registro con implementazione completa (UI + API).
- **Tempo di risposta**: < 500ms p95 per endpoint dei widget principali.
- **Adozione focus mode**: ≥ 60% degli utenti attiva la modalità almeno una volta a settimana.
- **Tasso errore salvataggio layout**: < 0,5% delle richieste.
- **Engagement timeline**: ≥ 3 interazioni per sessione con eventi timeline (azioni rapide o aperture dettagli).

## 6. Prossimi Passi Operativi
1. Validare la roadmap con product owner e responsabili di reparto (Direzione, Manutenzione, Reception) per definire priorità dei widget.
2. Redigere schede tecniche per ciascun widget mancante (dati, permessi, interazioni) e assegnare ownership a team frontend/backend.
3. Preparare una branch di hardening per consolidare gli endpoint e rimuovere componenti legacy (`frontend/src/widgets/AnnouncementsWidget.jsx`).
4. Attivare un canale di feedback continuo (es. survey in-app) per raccogliere percezioni post-rilascio e iterare velocemente.

Seguendo questo blueprint, la Home Desk evolverà da showcase grafico a "control tower" realmente operativa, garantendo ai diversi ruoli aziendali informazioni aggiornate, azioni rapide e automazioni intelligenti.
