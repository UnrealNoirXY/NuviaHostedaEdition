# Sprint 0 — Audit & Baseline (Bacheca HR Portal)

## 1) Mappatura flussi attuali (Bacheca = HR Portal in modalità bacheca)

**Contesto:** la Bacheca è la stessa SPA HR Portal montata con `portalMode = "bacheca"`. Il template `bacheca_root.html` passa il flag via `data-portal-mode`, e la SPA usa `HrPortalApp` per orchestrare il caricamento dei dati. 【F:hr_portal/templates/hr_portal/bacheca_root.html†L1-L10】【F:frontend/src/modules/hr/HrPortalApp.jsx†L1139-L1144】

```mermaid
flowchart TD
    A[Utente accede a /hr/bacheca] --> B[BachecaNuviaView rende bacheca_root.html]
    B --> C[DOM: #root data-portal-mode="bacheca"]
    C --> D[HR Portal SPA (HrPortalApp)]
    D --> E[GET /api/hr/context/]
    E --> F{Permessi e contesto}
    F --> G[Step 0: Bacheca Nuvia]
    G --> H[GET /api/hr/notifications/]
    G --> I[GET /api/hr/documents/]
    G --> J[GET /api/hr/payslips/]
    H --> K[Cards comunicazioni + highlights]
    I --> L[Documenti con ACK richiesto]
    J --> M[Storico buste paga + download]
```

**Criticità UX (flow & contenuto):**
- **Percorso bacheca = step 0, ma la UI rimane identica alla modalità HR completa.** In modalità bacheca l’utente vede lo stesso layout e la stessa struttura di componenti di `HrPortalApp`, con la differenza che le sezioni HR “step 1+” vengono nascoste. Questo può generare **aspettative errate** perché il design è quello di un flusso multi‑step “HR admin” (titoli, card e summary grid molto ricchi) anche per un utente che vuole solo bacheca. 【F:frontend/src/modules/hr/HrPortalApp.jsx†L2215-L2420】
- **Sezioni principali molto dense per un home “personale”.** La bacheca presenta insieme summary grid, overview grid e tre sotto‑sezioni (buste paga, documenti, comunicazioni), creando **cognitive load elevato** per la prima schermata. Non ci sono meccanismi di “progressive disclosure” (collassabili, paging, o highlight con CTA). 【F:frontend/src/modules/hr/HrPortalApp.jsx†L2215-L2390】
- **Azioni primarie disperse tra sottosezioni.** Le CTA “Aggiorna” sono ripetute in ogni blocco, mentre azioni chiave (ack documento, download busta) sono inglobate nei singoli list component: l’utente non percepisce a colpo d’occhio la **priorità** tra “leggi documento” e “scarica busta paga”. 【F:frontend/src/modules/hr/HrPortalApp.jsx†L2269-L2340】

## 2) Analisi UX Mobile (breakpoint unico a 960px)

**Riferimento CSS:** è presente un solo breakpoint generale a `@media (max-width: 960px)` che forza i layout a colonna singola e i pulsanti full‑width. Non ci sono aggiustamenti specifici per schermi 360/390/414/768. 【F:frontend/src/hr-portal.css†L121-L178】【F:frontend/src/hr-portal.css†L837-L876】

### Problemi UI per dimensioni schermo

**360px (phone small)**
- **Header sticky troppo alto:** l’header con `padding: 16px 20px` + card “scope” (min-width 180) prende molta altezza verticale, lasciando poco spazio sopra la piega. 【F:frontend/src/hr-portal.css†L18-L87】
- **Liste con `justify-content: space-between`** nelle overview list: su testi lunghi (titolo comunicazione/documento) il contenuto tende a spezzarsi, creando righe poco leggibili e badge “staccati”. 【F:frontend/src/hr-portal.css†L150-L166】
- **CTA ridondanti e full‑width:** con layout a colonna unica, i pulsanti “Aggiorna” diventano sempre full‑width e ripetuti, aumentando il rumore visivo. 【F:frontend/src/hr-portal.css†L842-L872】

**390px (phone medium)**
- **Spaziatura eccessiva nei blocchi principali:** padding costante (24px + 16px) fa crescere l’altezza dei moduli; la bacheca risulta “lunghissima” con scroll eccessivo. 【F:frontend/src/hr-portal.css†L18-L110】
- **Quick filters in wrap:** i filtri rapidi diventano due o tre righe, ma senza un meccanismo di “overflow” o “collapse”, facendo percepire la sezione come secondaria ma visivamente ingombrante. 【F:frontend/src/hr-portal.css†L189-L214】

**414px (phone large)**
- **Griglie forzate a colonna singola anche dove si potrebbe mantenere una doppia colonna.** Con min‑width delle card (220/280/320), lo switch a 960px forza la stessa vista di 360px, perdendo densità informativa. 【F:frontend/src/hr-portal.css†L121-L178】【F:frontend/src/hr-portal.css†L248-L256】
- **Titoli e sottotitoli non scalano:** dimensioni tipografiche fisse per titoli e eyebrow label, senza riduzioni specifiche per mobile. 【F:frontend/src/hr-portal.css†L18-L70】

**768px (tablet)**
- **Breakpoint troppo aggressivo:** a 768px si applica la stessa vista “mobile phone”, con griglie tutte a 1 colonna e pulsanti full‑width: l’UI appare “sprecata” e con densità bassa. 【F:frontend/src/hr-portal.css†L121-L178】【F:frontend/src/hr-portal.css†L842-L872】
- **Header sticky + colonne singole:** la perdita delle colonne lascia molto spazio verticale, ma la header sticky resta grande, riducendo l’area utile per i contenuti principali. 【F:frontend/src/hr-portal.css†L18-L87】

## 3) Baseline KPI (HREventLog e KPI view)

**Eventi disponibili (HREventLog):** tra gli eventi già tracciati, quelli legati alla bacheca sono `document_ack` e `payslip_download` (oltre ad eventi di notifica e batch). 【F:hr_portal/models.py†L979-L1013】

**KPI baseline (definizioni attuali):**

| KPI | Definizione | Fonte dati / evento | Note |
| --- | --- | --- | --- |
| Tasso download buste paga | `downloaded / total` | `Payslip.downloaded_at` + evento `payslip_download` | Il calcolo attuale in `HRKPIView` usa il campo `downloaded_at`; l’evento è comunque disponibile per analisi raw. 【F:hr_portal/views.py†L1228-L1242】【F:hr_portal/models.py†L979-L1003】 |
| Tasso ACK documenti | `acknowledged / required` | `HRDocument.acknowledged_by` + evento `document_ack` | KPI in `HRKPIView` usa la relazione `acknowledged_by`; l’evento consente un tracciamento cronologico. 【F:hr_portal/views.py†L1243-L1256】【F:hr_portal/models.py†L979-L1003】 |
| Email delivery rate buste paga | `sent / (sent + failed)` | Eventi `payslip_email_sent` e `payslip_email_failed` | KPI già esposto dalla API per audit. 【F:hr_portal/views.py†L1233-L1252】【F:hr_portal/models.py†L979-L1007】 |

**Nota:** Gli eventi HREventLog consentono di ricostruire serie temporali (per resort/azienda) grazie agli indici su `event_type` e `created_at`. 【F:hr_portal/models.py†L1005-L1013】
