# Nuvia / Noir Tools Kit — Analisi Ultradettagliata e Piano di Ridisegno

> Documento master. Sostituisce di fatto i 28 file `.md` di analisi sparsi nella root.
> Obiettivo: rendere il programma **stabile, coerente e realmente utilizzabile al 100%**.
> Data analisi: 2026-06-30 · Branch: `claude/program-analysis-redesign-sfai0h`

---

## 0. Verdetto in una pagina

**Cos'è davvero il programma.** Un monolite Django 5.2 (suite gestionale per hotel/resort)
con **~26 app**, ~64.000 righe di Python, **189 template HTML**, **3 frontend JavaScript
diversi e in conflitto**, **28 documenti di pianificazione** in root e **187 migrazioni**.
Non è un prototipo: è un prodotto cresciuto per accumulo, senza un'architettura di riferimento.

**Il problema non è la mancanza di funzioni — è il contrario.** Ci sono troppe funzioni,
troppi strumenti aperti a metà, troppi "piani" mai chiusi. Il risultato è un sistema che
*fa molte cose male* invece di *poche cose benissimo*. "Renderlo 100% utile" significa
**consolidare e finire**, non aggiungere.

**Le 5 ferite più gravi (in ordine di urgenza):**

1. **Tre frontend in competizione** — `frontend/` (Vite+React, l'unico vivo), `frontend-next/`
   (Next.js, **orfano**: zero riferimenti nel backend), `frontend_legacy/` (React vecchio,
   **morto**). Più i template Django classici + il "desk" desktop-simulation. Nessuna fonte
   di verità per la UI.
2. **Nessun design system.** 189 template, 3 `base*.html`, CSS sparso per modulo, Bootstrap 5
   misto a SCSS custom misto a CSS-in-JS React. Ogni schermata ha un look diverso.
3. **God-module `core`** — `core/views.py` da **2.766 righe / 85 viste**, che importa modelli
   da 13 app diverse (auth, mail, 2FA, dashboard, reporting, resort, room…). È il collo di
   bottiglia di tutto.
4. **Autorizzazioni incoerenti e fragili.** Mix di `is_superuser`, `role in {...}` hardcoded,
   flag `has_X_access`, controlli `request.user.role == '...'` sparsi inline. La sidebar/hub
   è cablata a mano in `get_hub_tools`. Nessun layer di permessi centralizzato.
5. **Igiene del repo compromessa.** Backup SQLite da **2.6 MB committato in git**, immagini da
   **7.9 MB** (`login-background.jpg`), README che descrive un prodotto diverso (un assistente
   AI "AIDA" mai costruito), CI che gira solo `manage.py test` su `main`.

---

## 1. Mappa funzionale reale (cosa esiste davvero)

| Dominio | App | LOC py | Stato reale |
|---|---|---|---|
| Identità / core / hub / mail | `accounts`, `core` | 7.345 | **Sovraccarico.** core fa troppo |
| Manutenzioni / ticket | `tickets`, `resort`, `assets` | 3.747 | Funzionale, frontend React parziale |
| Recensioni (sentiment) | `reviews` | 3.343 | Pesante (transformers, nltk) |
| HR / buste paga / OCR | `hr_portal` | 6.104 | **Enorme**, models 1.909 righe |
| Prenotazioni / check-in | `bookings` | 3.763 | models 666 righe, ambizioso |
| Menu Creation Studio | `menu_generator` | 3.462 | WeasyPrint/PDF, molto codice |
| Finanza / economato / ordini | `financials`, `economato`, `purchase_orders`, `inventory` | 4.484 | 4 app che si sovrappongono |
| Desk / desktop simulation | `desk`, `frontend/` | — | "OS nel browser", concept |
| Supporto IT / procedure / doc | `it_support`, `procedures`, `documents`, `document_verification` | 2.354 | Frammentati |
| Comunicazioni / notifiche | `communications`, `notifications` | 2.082 | Email + push, sovrapposti |
| Competitor / svago / skills / cards | `competitors`, `svago`, `skills`, `profile_cards` | 2.991 | Side-projects |

**Osservazione strutturale:** quattro app (`financials`, `economato`, `purchase_orders`,
`inventory`) coprono lo stesso dominio "soldi e magazzino" senza un confine chiaro. Stesso
discorso per `communications`+`notifications` e per `documents`+`document_verification`.

---

## 2. Problemi ARCHITETTURALI (causa radice)

### 2.1 Frammentazione del frontend — **P0, la priorità n.1**
- `frontend-next/` e `frontend_legacy/` non sono referenziati da nessun `.py`/`.html`:
  **codice morto** che confonde, gonfia il repo e fa credere che esista una "v2".
- L'unico frontend vivo è `frontend/` (Vite + React 19, integrato via `django-vite`).
- Coesistono **due paradigmi UI opposti**: pagine server-rendered (template Django + Bootstrap)
  e una "desktop simulation" React (window manager, taskbar, spotlight). Nessuna regola su
  quando usare l'uno o l'altro.
- **Effetto:** ogni nuova feature deve scegliere uno stack a caso → debito che si moltiplica.

### 2.2 God-module `core`
- `core/views.py`: 2.766 righe, 85 viste, 58 import. Mescola login/2FA/password, hub, dashboard
  multi-ruolo, reporting, CRUD resort/room, e **un intero client email "Nuvia Mail"**
  (compliance, OAuth, code di invio) che dovrebbe essere un'app a sé.
- `core/models.py`: 491 righe. `core` importa modelli da 13 app → **dipendenze circolari
  latenti** e impossibilità di testare in isolamento.

### 2.3 Esplosione documentale
- 28 `.md` in root + altri dentro le app (es. `hr_portal/ANALISI_*`, `SPRINT0_AUDIT.md`).
  Sono "piani" e "proposte" sovrapposti (`HOME_DESK_PROPOSAL` vs `_V2_PROPOSAL` vs
  `_REVOLUTION_PLAN` vs `_INNOVATION_PLAN`…). Nessuno è la fonte di verità.
- Il `README.md` descrive un assistente AI RAG ("AIDA") che **non esiste nel codice**.

### 2.4 Igiene repository / build
- `db.sqlite3.bak.2025-09-02-0806` (**2.6 MB**) committato — possibile **dato sensibile reale**.
- Asset non ottimizzati committati: `login-background.jpg` 7.9 MB, `favicon.ico` 724 KB,
  `logo.png` 512 KB, screenshot di debug (`nuvia_error_nav.png`).
- Due `package-lock.json` da ~300–370 KB (frontend + frontend-next morto).
- `frontend/dist` non committato → in produzione serve un build step, ma la pipeline non lo fa.

### 2.5 Modelli "god"
- `hr_portal/models.py` 1.909 righe, `bookings/models.py` 666, `menu_generator/models.py` 623.
  Vanno spezzati per sottodominio.

---

## 3. Problemi di LOGICA

1. **Autorizzazione non centralizzata.** Coesistono: `user.is_superuser`,
   `user.role in {SUPERADMIN, OWNER, ...}` (cablato in `get_hub_tools`), flag dinamici
   `has_maintenance_access`/`has_reviews_access`/`has_inventory_access`, e confronti
   `request.user.role == '...'` sparsi nelle viste. **Rischio reale:** una schermata visibile
   nell'hub ma con la viewset che non ricontrolla il permesso (o viceversa). Serve un singolo
   `permissions.py` per ruolo→capacità, usato sia dalla navigazione sia dalle viste.
2. **Navigazione hardcoded.** L'hub è una lista costruita a mano in Python (`add_tool(...)`):
   aggiungere/spostare uno strumento richiede modificare codice e ridurre la testabilità.
   Dovrebbe essere un registry dichiarativo (per app) + filtro per permessi.
3. **Domini sovrapposti senza contratto.** `financials` legge da `purchase_orders`/`economato`
   ma i confini non sono definiti → logiche duplicate di budget/consuntivo.
4. **Solo 1 `TODO/FIXME` nel codice** a fronte di 28 documenti di "cose da fare": il debito non
   è tracciato dove serve (nel codice/issue) ma in markdown che nessuno chiude.
5. **Configurazione fragile.** `DJANGO_VITE_DEV_MODE = ... default=False if DEBUG else False`
   (ramo inutile, sempre False), `SESSION_COOKIE_DOMAIN` default `None`, `CSRF_COOKIE_HTTPONLY=False`
   globale. Logica di sicurezza decisa per default impliciti.

---

## 4. Problemi di FRONTEND / UX / GRAFICA

1. **Nessuna identità visiva unica.** 3 `base*.html`, Bootstrap + SCSS custom + CSS-in-JS:
   tipografia, spaziature, colori e componenti (bottoni, tabelle, modali) divergono per modulo.
2. **Due modelli mentali per l'utente.** Pagine "classiche" (link, form, tabelle) accanto al
   "desktop nel browser" (finestre, taskbar). L'utente non sa mai cosa aspettarsi.
3. **Accessibilità e mobile non governati.** Esistono componenti "MobileOS"/"MobileSheet" ad hoc
   invece di un layout responsive unico → manutenzione doppia.
4. **Stato e dati frontend disomogenei.** `axios` + `js-cookie` + fetch nativo nel Next morto;
   nessuna libreria di data-fetching/caching condivisa, nessun design token, nessuna libreria
   componenti riusabile.
5. **Performance percepita.** Asset pesanti (sfondi multi-MB) caricati al login; nessuna
   strategia di lazy-loading/code-splitting documentata oltre al PWA workbox.

---

## 5. Problemi di SICUREZZA / CONFIG / QUALITÀ

- **Segreti/dati in repo:** backup DB SQLite committato. Da rimuovere dalla history e ruotare
  eventuali credenziali contenute.
- **CI debole:** gira solo `manage.py test` su push/PR a `main`; nessun lint (ruff/flake8),
  nessun build frontend, nessun controllo migrazioni, nessuna coverage. 39 file di test per
  64k righe = copertura bassa e non misurata.
- **`SECRET_KEY` con default insicuro** e `CSRF_COOKIE_HTTPONLY=False` globali: accettabili in
  dev, ma vanno forzati/verificati in produzione tramite check espliciti.
- **Dipendenze ML pesanti** (`transformers`, `sentencepiece`, `opencv`, `matplotlib`, `pandas`)
  caricate nel monolite web: peso, tempi di avvio e superficie di attacco. Vanno isolate in
  worker/servizi.

---

## 6. PIANO DI RIDISEGNO

Principio guida: **prima consolidare e stabilizzare, poi unificare la UI, poi rifinire i
moduli uno a uno.** Niente nuove feature finché le fondamenta non sono pulite.

### FASE 0 — Bonifica e fondamenta (1–2 settimane) · **P0**
Obiettivo: repo pulito, una sola direzione tecnica, niente codice morto.
- [ ] **Eliminare i frontend morti** `frontend-next/` e `frontend_legacy/` (sono orfani).
      Decisione: **`frontend/` (Vite+React) è la fonte di verità unica del frontend ricco.**
- [ ] **Rimuovere dalla history** `db.sqlite3.bak.*` e gli asset di debug; aggiungere a
      `.gitignore`; ruotare eventuali credenziali presenti nel backup.
- [ ] **Ottimizzare gli asset** (sfondi → WebP < 300 KB, favicon corretta).
- [ ] **Consolidare la documentazione**: questo file diventa il master; archiviare i 28 `.md`
      in `docs/archive/`. Riscrivere `README.md` per descrivere il prodotto reale.
- [ ] **Rafforzare la CI**: aggiungere `ruff` (lint), `python manage.py makemigrations --check`,
      build del frontend, e far girare i test anche sul branch di feature (non solo `main`).

### FASE 1 — Layer di logica trasversale (2–3 settimane) · **P0/P1**
Obiettivo: una sola verità per permessi e navigazione.
- [ ] **`core/permissions.py` unico**: mappa dichiarativa ruolo → capacità; helper
      `user_can(user, capability)`. Sostituire tutti i `role in {...}` e `has_X_access` sparsi.
- [ ] **Registry di navigazione dichiarativo**: ogni app registra i propri "tool"
      (label, icona, url, capability richiesta). L'hub e la sidebar si generano filtrando per
      permesso. Elimina l'hardcoding di `get_hub_tools`.
- [ ] **Spezzare `core`**: estrarre "Nuvia Mail" in un'app `mailbox/` dedicata; spostare le
      dashboard per-ruolo e il reporting in moduli separati. `core` torna a contenere solo
      identità/hub/util condivisi.
- [ ] **Settings espliciti e sicuri** (rimuovere rami morti, check di produzione su cookie/CSRF).

### FASE 2 — Unificazione UI e design system (3–4 settimane) · **P1**
Obiettivo: un solo linguaggio visivo, una sola shell.
- [ ] **Scelta del paradigma** (vedi §7, serve decisione): UI applicativa coerente **oppure**
      la "desktop simulation" come shell ufficiale — **non entrambi**.
- [ ] **Design tokens** (colori, tipografia, spaziature, raggi, ombre) + **libreria componenti
      React** riusabile (bottoni, tabelle, form, modali, toast, empty/loading states).
- [ ] **Una sola `base.html`** + una sola shell di navigazione (top bar + sidebar generata dal
      registry). Deprecare `base_demo`/`base_landing` come varianti minime.
- [ ] **Data-fetching standard** (un client unico, gestione errori/loading uniforme) e
      responsive-first (eliminare i componenti "MobileOS" ad hoc).

### FASE 3 — Ridisegno dei moduli, a ondate (continuativo) · **P1/P2**
Per ogni modulo, nell'ordine, applicare lo stesso template di lavoro:
*audit funzionale → definizione confini → riallineamento dati → UI sul design system → test.*
- **Ondata 1 (valore alto, già maturi):** Manutenzioni/Ticket, Recensioni, Prenotazioni.
- **Ondata 2 (consolidare i domini sovrapposti):** unificare il dominio "finanza+magazzino"
  (`financials`/`economato`/`purchase_orders`/`inventory`) sotto confini chiari; unificare
  `communications`/`notifications` in un solo centro messaggi.
- **Ondata 3 (alleggerire e finire):** HR portal (spezzare i model giant, isolare OCR in worker),
  Menu Studio (isolare la generazione PDF), e side-projects (`svago`, `skills`, `competitors`,
  `profile_cards`) — decidere per ciascuno: **finire, fondere o rimuovere.**

### FASE 4 — Qualità e affidabilità (continuativo) · **P2**
- [ ] Coverage misurata, test su ogni view critica e sul layer permessi.
- [ ] Isolare le dipendenze ML pesanti dietro task Celery / servizio separato.
- [ ] Osservabilità: il logging strutturato esiste già (`core.logging_utils`) → estenderlo a
      metriche d'uso per capire quali strumenti servono davvero (e quali tagliare).

---

## 7. Decisioni che servono da te (bloccano le fasi)

1. **Frontend (Fase 2):** vogliamo una **UI applicativa classica e coerente** (consigliata: più
   veloce da rendere utile) oppure puntiamo sulla **"desktop simulation" come prodotto**? Da
   questa scelta dipende tutta la Fase 2.
2. **Scope dei moduli (Fase 3):** quali sono i 3–4 moduli *davvero core* per il business
   (es. Prenotazioni, Manutenzioni, HR, Finanza)? Tutto il resto va in coda o tagliato.
3. **Dato in `db.sqlite3.bak`:** è un backup reale di produzione? Se sì va trattato come
   incidente (rimozione dalla history + rotazione credenziali).
4. **Da dove partiamo subito:** propongo **Fase 0** (bonifica) perché è a basso rischio e sblocca
   tutto il resto. Confermi?

---

## 8. Quick wins immediati (basso rischio, alto segnale)
1. Cancellare `frontend-next/` e `frontend_legacy/` (codice morto verificato).
2. Rimuovere il backup SQLite e gli screenshot di debug dal repo.
3. Riscrivere il README sul prodotto reale + archiviare i 28 `.md`.
4. Aggiungere `ruff` e il check migrazioni alla CI.
5. Comprimere gli asset multi-MB del login.

> Tutti i punti della Fase 0 sono eseguibili subito senza toccare la logica di business.
