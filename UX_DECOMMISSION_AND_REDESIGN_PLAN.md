# Analisi UX e piano di dismissione moduli esterni

Data analisi: 2026-07-10

## Stato attuale osservato

### Screenshot disponibili nello stato repository

> Nota operativa: non è stato possibile avviare l'app Django in questo container perché le dipendenze Python non sono installate e `pip install -r requirements.txt` è bloccato dal proxy PyPI (`Tunnel connection failed: 403 Forbidden`). Gli screenshot runtime nuovi non sono quindi producibili qui; sotto elenco gli screenshot già presenti nel repository da usare come riferimento visuale dello stato attuale.

| Area | File screenshot | Uso nell'analisi |
| --- | --- | --- |
| Navigazione / errore UI | `screenshots/nuvia_error_nav.png` | Verifica densità della navigazione e presenza di stato errore. |
| Dashboard demo | `static/img/demos/dashboard_demo.png` | Riferimento visuale per card, KPI e gerarchia dashboard. |
| Ticket demo | `static/img/demos/tickets_demo.png` | Riferimento visuale del modulo ticket da dismettere/sostituire. |
| Reviews demo | `static/img/demos/reviews_demo.png` | Riferimento di layout data-heavy già più maturo. |

## Moduli da eliminare o scollegare

L'obiettivo dichiarato è rimuovere dall'esperienza principale i moduli già sviluppati esternamente:

1. **Menu Creation Studio / Menu editor**
   - App installata: `menu_generator`.
   - URL pubblico interno: `/menu-generator/`.
   - Voce sidebar: `Menu Creation Studio`.
   - Asset React/Vite dedicati in `frontend/src/apps/menu_generator/`.

2. **Client mail / Nuvia Mail**
   - Template principali: `core/templates/core/nuvia_mail_landing.html` e `core/templates/core/nuvia_mail_workspace.html`.
   - Voce sidebar: `Nuvia Mail`.
   - Probabile funzione utile residua: report programmati e notifiche email di sistema, che sono diversi dal client mail e vanno preservati se servono all'operatività.

3. **Programmi ticket**
   - Ticket manutenzione: app `tickets`, URL sotto `/maintenance/ticket/`, dashboard e API `/api/maintenance/`.
   - Ticket IT: app `it_support`, URL `/supporto-it/`, chat e report.
   - Importante: prima della rimozione bisogna separare ciò che è "programma ticket" da eventuali KPI storici, notifiche o alert ancora usati da dashboard direzionali.

## Diagnosi UX

### 1. Navigazione troppo ampia e poco prioritaria

La sidebar mescola navigazione principale, strumenti, amministrazione globale e gestione operativa. Per un utente non tecnico l'effetto è di piattaforma complessa, con troppe destinazioni concorrenti. La presenza contemporanea di Home Desk, manutenzione, Supporto IT, Menu Creation Studio, Nuvia Mail, dashboard direzionali e amministrazione rende difficile capire "cosa devo fare adesso".

**Impatto UX:** aumento del tempo di orientamento, errori di click, percezione di prodotto non rifinito.

**Intervento:** ridurre a 5-7 entry primarie, spostare il resto in launcher/command palette o in impostazioni amministrative.

### 2. Funzionalità duplicate o fuori perimetro

Menu editor, mail client e ticket competono con strumenti esterni già scelti. Tenerli visibili crea due problemi: l'utente può usare il canale sbagliato e il prodotto sembra incoerente.

**Intervento:** introdurre feature flag di dismissione immediata e poi rimuovere URL, template e app in una seconda fase.

### 3. Dashboard non abbastanza orientata all'azione

La dashboard demo mostra card e KPI, ma il valore UX cresce se ogni card risponde a tre domande: stato, priorità, prossima azione. Le sezioni data-heavy devono essere meno tabellari e più operative.

**Intervento:** nuovo hub con blocchi "Oggi", "Da approvare", "Alert", "Ultime attività", "Scorciatoie ruolo".

### 4. Stile visivo da uniformare

Il prodotto ha già una base moderna (sidebar shell, card, PWA/mobile shell), ma i moduli storici Django/template e i moduli React hanno linguaggi visivi diversi.

**Intervento:** design system minimo: palette, spacing scale, card elevation, tipografia, stati vuoti, badge, pulsanti e skeleton loading condivisi.

## Piano operativo consigliato

### Fase 0 - Backup e mappa dipendenze (0,5 giornata)

- Creare branch dedicato.
- Esportare elenco URL e permessi dei tre moduli.
- Verificare dati storici da preservare con dump database per tabelle `tickets_*`, `it_support_*`, `menu_generator_*` se vanno archiviate.
- Definire se i link devono sparire o puntare ai servizi esterni.

### Fase 1 - Dismissione soft via UX (1 giornata)

- Rimuovere dalla sidebar:
  - `Menu Creation Studio`.
  - `Nuvia Mail`.
  - `Supporto IT` e dashboard ticket, se il ticketing esterno è già operativo.
- Lasciare URL tecnici protetti con pagina "Modulo dismesso" o redirect al servizio esterno.
- Aggiungere variabili settings/env:
  - `ENABLE_MENU_GENERATOR=false`.
  - `ENABLE_NUVIA_MAIL=false`.
  - `ENABLE_INTERNAL_TICKETS=false`.
  - `EXTERNAL_TICKETS_URL`, `EXTERNAL_MAIL_URL`, `EXTERNAL_MENU_URL` se servono redirect.

### Fase 2 - Pulizia tecnica controllata (2-4 giornate)

- Scollegare URL include da `gestione_manutenzioni/urls.py`.
- Rimuovere app da `INSTALLED_APPS` solo dopo aver gestito migrazioni, FK e admin.
- Eliminare template e bundle non più referenziati.
- Preservare solo notifiche email di sistema se non fanno parte del client mail.
- Aggiornare test, sitemap interna, PWA/service worker e permessi utente.

### Fase 3 - Redesign UX del core (4-8 giornate)

- Ridisegnare Home Desk come vera pagina di atterraggio:
  - Header con saluto, struttura selezionata, search globale.
  - Widget azionabili per ruolo.
  - CTA primarie massimo 2 per pagina.
  - Stato sistema e notifiche compatte.
- Nuova sidebar:
  - `Home`.
  - `Operazioni`.
  - `HR e Comunicazioni`.
  - `Inventario / Economato`.
  - `Direzione`.
  - `Amministrazione`.
  - `Impostazioni`.
- Aggiungere breadcrumb e titoli pagina coerenti.
- Standardizzare empty states: icona, testo breve, CTA unica.
- Mobile: bottom navigation per 4 sezioni principali e drawer per il resto.

### Fase 4 - Validazione qualità (1-2 giornate)

- Smoke test URL principali per ogni ruolo.
- Test permessi: superadmin, owner, director, manutentore, HR, economato.
- Test responsive 390px, 768px, 1440px.
- Lighthouse/performance sulle pagine principali.
- Sessione con 2-3 utenti reali: task "trova una procedura", "apri HR", "leggi comunicazione", "controlla inventario".

## Backlog UX prioritizzato

| Priorità | Intervento | Risultato atteso |
| --- | --- | --- |
| P0 | Nascondere moduli dismessi dalla navigazione | Riduzione confusione immediata. |
| P0 | Redirect o pagina dismissione per vecchi URL | Nessun 404 brusco e migrazione più sicura. |
| P1 | Nuova architettura sidebar per categorie | Orientamento più rapido. |
| P1 | Home Desk con azioni per ruolo | Meno click e maggiore valore percepito. |
| P1 | Design tokens e componenti base | Coerenza visiva tra Django e React. |
| P2 | Command palette/search globale | Navigazione veloce per power user. |
| P2 | Audit accessibilità contrasto/focus | Prodotto più professionale e usabile. |
| P3 | Animazioni micro-interaction | Esperienza più premium, non bloccante. |

## Rischi da gestire

- **Rotture di import o reverse URL:** la sidebar e alcune dashboard usano `{% url %}`; se si rimuove un'app senza togliere i riferimenti, il rendering fallisce.
- **Migrazioni e dati storici:** eliminare app Django può complicare future migrazioni se altre tabelle referenziano modelli rimossi.
- **Permessi residui:** campi come `menu_creation_studio_enabled` o accessi ticket possono restare nell'utente e confondere l'admin.
- **Email di sistema:** non confondere client mail con invio email transazionali, reset password, notifiche e report programmati.

## Definition of Done per la prima release bella e funzionante

- La sidebar non mostra più Menu Creation Studio, Nuvia Mail e ticket interni.
- Gli URL legacy hanno comportamento controllato: redirect esterno o pagina dismissione.
- Home Desk è la landing operativa principale e mostra solo azioni pertinenti al ruolo.
- Le pagine core usano card, pulsanti, badge e spaziature coerenti.
- Nessun errore di reverse URL nei template.
- Test smoke su login, hub, Home Desk, HR, procedure, inventario/economato e amministrazione.
