# Analisi dettagliata HR Portal: criticità funzionali, preview buste paga e piano di miglioramento

## Contesto
Questa analisi risponde ai problemi segnalati:
1. sezione HR Portal percepita come non funzionale;
2. preview buste paga non affidabile/non chiara;
3. interfaccia troppo confusionaria.

L'obiettivo è individuare cause tecniche + UX e proporre un piano operativo in fasi, con priorità e criteri di successo.

---

## 1) Diagnosi: perché oggi il portale risulta “confusionario”

### 1.1 Frontend monolitico (alto debito di manutenibilità)
- Il componente principale `HrPortalApp.jsx` è molto esteso (oltre 4600 righe) e concentra in un unico file:
  - dashboard,
  - gestione documenti,
  - preview/import buste paga,
  - KPI/incident playbook,
  - comunicazioni,
  - ticketing,
  - preferenze.
- Questa struttura rende difficile:
  - capire i flussi,
  - testare in modo mirato,
  - evitare regressioni.

### 1.2 IA (information architecture) non gerarchica
- La UI mostra numerosi step nello stesso contesto (anche step “tecnici” avanzati come playbook incidenti), con carico cognitivo elevato.
- L'utente HR operativo (caricare/assegnare/confermare buste paga) e l'utente manageriale (monitorare KPI) condividono la stessa superficie con poca separazione per intento.

### 1.3 “Troppa UI, poca guida”
- Sono presenti molti badge, card e metriche, ma il percorso primario non è chiaramente guidato da un wizard lineare “upload → preview → correzioni → conferma → creazione batch”.
- L'utente può perdersi tra elementi informativi non bloccanti e azioni critiche.

---

## 2) Diagnosi preview: perché viene percepita come “non funziona”

### 2.1 Duplicazione di metodo backend nella viewset preview
Nel `PayslipBatchViewSet` esistono due metodi con lo stesso nome Python `preview_stream`:
- uno per `detail=True` (stream dello stato batch),
- uno per `detail=False` (stream per token preview job).

A livello classe Python, il secondo metodo sovrascrive il primo nome. Questo è un forte odore architetturale e può generare comportamento inatteso/fragile sul routing delle action DRF.

### 2.2 Capacità dichiarate non coerenti tra endpoint
- L'endpoint `preview` restituisce capability con `stream_available: false` e `polling_available: false`.
- Esistono però endpoint dedicati `preview-start`, `preview-status/<token>`, `preview-stream/<token>`, `preview-fallback`.

Per frontend/operatore questo crea ambiguità su “quale modalità usare davvero”.

### 2.3 Affidabilità realtime dipendente da SSE
- Il flusso live usa `EventSource` su stream SSE.
- In ambienti reali (proxy/buffering/network policy) SSE può degradare.
- È presente logica fallback lato backend (evento `preview_fallback_polling`), ma va resa esplicita e sempre visibile in UX con passaggio automatico e stato chiaro.

### 2.4 UX della preview orientata a metrica più che a verifica operativa
- Lo spazio UI include molte informazioni di KPI/incident, ma il bisogno principale è: vedere segmenti, controllare errori, assegnare rapidamente, confermare con fiducia.
- Se questa traiettoria non è dominante, l'utente conclude che “la preview non aiuta”.

---

## 3) Root cause sintetiche (priorità)

### P0 (impatto massimo)
1. Flusso primario non lineare e non “task-first”.
2. Ambiguità tecnica preview (metodi/action sovrapposti + capability incoerenti).
3. Assenza di separazione netta tra area operativa e area osservabilità.

### P1
1. Componente frontend monolitico con bassa testabilità.
2. Copertura test limitata sulle interazioni UX critiche end-to-end.

### P2
1. Linguaggio UI troppo tecnico in contesto operativo.
2. Mancanza di progressive disclosure (prima azioni essenziali, poi dettagli avanzati).

---

## 4) Piano migliorativo proposto

## Fase 0 (1 settimana) – Stabilizzazione rapida e “deconfusione”

### Obiettivo
Rendere immediatamente usabile il percorso preview/import buste paga.

### Interventi
1. **Fix naming backend preview action**
   - Rinominare i metodi in modo univoco (es. `preview_stream_batch` e `preview_stream_job`) mantenendo gli stessi `url_path` necessari.
2. **Contratto capability coerente**
   - Uniformare la semantica `capabilities` tra endpoint sync e async.
3. **Flusso UI guidato**
   - In testata sezione “Buste paga”, introdurre wizard esplicito a 5 step:
     `Upload` → `Preview` → `Correzioni` → `Conferma` → `Crea batch`.
4. **Fallback automatico e visibile**
   - Se SSE fallisce, switch automatico a polling con banner persistente informativo.
5. **Riduzione rumore in schermata operativa**
   - Spostare i blocchi KPI/incident avanzati in pannello secondario collapsible o in pagina dedicata.

### KPI di uscita fase 0
- Tasso completamento preview→conferma +20%.
- Riduzione errori “preview bloccata/non aggiorna”.
- Tempo medio “upload→conferma” ridotto.

---

## Fase 1 (1-2 settimane) – Refactoring front-end strutturale

### Obiettivo
Ridurre la complessità per utente e team sviluppo.

### Interventi
1. **Spezzare `HrPortalApp.jsx` in moduli**
   - `PayrollWorkspace` (core operativo).
   - `PayrollMonitoring` (KPI/incident).
   - `DocumentsWorkspace`, `NotificationsWorkspace`, `TicketsWorkspace`, `PreferencesWorkspace`.
2. **Separazione routing/tabs per profilo intento**
   - Tab “Operatività” (default HR specialist).
   - Tab “Monitoraggio” (owner/superadmin/HR lead).
3. **State management semplificato**
   - Isolare stato preview in hook dedicato (`usePayslipPreviewFlow`).
4. **Test UI del percorso critico**
   - Coprire upload, stream success/fail, fallback polling, assegnazione manuale, conferma, submit batch.

### KPI di uscita fase 1
- Riduzione dimensione file principale (>60%).
- Aumento copertura test su percorso preview.
- Diminuzione bug regressivi legati alla preview.

---

## Fase 2 (2 settimane) – Qualità operativa e affidabilità produzione

### Obiettivo
Rendere il sistema robusto su carichi reali e facilmente supportabile.

### Interventi
1. **Osservabilità centrata su journey**
   - Dashboard funnel: `preview_started` → `preview_completed` → `preview_confirmed` → `batch_created`.
2. **Messaggistica errori azionabile**
   - Categorie: file invalido, parsing OCR, stream non disponibile, token scaduto, mismatch preview-token-create.
3. **Policy di degradazione controllata**
   - In assenza capability rendering/OCR, mostrare chiaramente modalità fallback senza bloccare il task.
4. **SLA operativi interni**
   - Tempo massimo preview per dimensione documento.
   - Alert automatici su failure/fallback rate.

### KPI di uscita fase 2
- Failure rate preview sotto soglia concordata.
- Ticket supporto HR su preview in calo stabile.

---

## 5) Piano UI/UX concreto (esperienza meno confusionaria)

1. **Primary Action bar sempre visibile**
   - Pulsanti principali: `Carica file`, `Avvia preview`, `Conferma preview`, `Crea batch`.
2. **Gerarchia visuale forte**
   - Sezione operativa in alto; analytics avanzata in basso o pagina separata.
3. **Progressive disclosure**
   - Default minimale; dettagli tecnici espandibili.
4. **Less is more sui badge**
   - Mostrare solo indicatori che cambiano la decisione utente.
5. **Copy orientato all'azione**
   - Testi brevi “cosa fare ora” e “prossimo step”.

---

## 6) Backlog priorizzato

### P0 (subito)
- [ ] Rinomina metodi duplicati preview stream backend.
- [ ] Allinea `capabilities` e scelta endpoint preview.
- [ ] Wizard operativo compatto in area buste paga.
- [ ] Fallback SSE→polling automatico con feedback visibile.

### P1
- [ ] Refactor `HrPortalApp.jsx` in moduli + hook dedicati.
- [ ] Spostamento KPI incident in workspace separata.
- [ ] Test E2E percorso upload/preview/conferma/create.

### P2
- [ ] Ottimizzazione performance su file grandi.
- [ ] Miglioramento microcopy e accessibilità.

---

## 7) Conclusione
Il problema non è solo “bug preview”: è una combinazione di **ambiguità tecnica + sovraccarico informativo + architettura frontend monolitica**.

Con il piano sopra:
- in pochi giorni si ottiene una UX più chiara e affidabile,
- in 2-4 settimane si costruisce una base realmente manutenibile,
- il portale passa da “ricco ma confuso” a “operativo, prevedibile e scalabile”.
