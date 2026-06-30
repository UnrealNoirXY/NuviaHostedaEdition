# Menu Creation Studio — Analisi approfondita e piano di rilancio

## 1) Diagnosi sintetica

Lo strumento ha una **base tecnologica promettente** (modello dati solido, API ampie, generazione documenti, permessi granulari), ma oggi espone agli chef una UX che risulta:

1. **Visivamente incoerente** (tema “premium” ma leggibilità altalenante).
2. **Cognitivamente pesante** (troppi percorsi e decisioni, poca guida contestuale).
3. **Fragile nel flusso operativo** (errori generici, feedback deboli, poca prevenzione degli errori).
4. **Lontana dal mental model di cucina** (utente pensa per “servizio/turno/menu del giorno”, non per entità tecniche separate).

In sintesi: la tecnologia è valida, ma l’interfaccia non traduce ancora bene il lavoro reale dello chef.

---

## 2) Cosa c’è già di buono (da preservare)

- **Accesso e governance**: controllo accessi e permessi per ruoli/strutture già ben impostato.
- **Capacità backend**: CRUD completo su piatti/layout/menu e validazione draft esistente.
- **Produzione documenti**: pipeline PDF/DOCX/ZIP già disponibile.
- **Versioning e audit trail**: basi utili per workflow professionali e compliance.

Indicazione strategica: non “rifare tutto”, ma **ripensare il layer UX** sopra fondamenta già valide.

---

## 3) Analisi UX profonda (problemi principali)

## 3.1 Architettura informativa confusa

L’entry point presenta più sezioni primarie (Piatti, Layouts, Menu, Cataloghi) e un wizard separato. Per un profilo chef il modello mentale è invece orientato a:

- “Creo il menu del servizio X”
- “Pesco piatti già pronti”
- “Applico uno stile approvato”
- “Pubblico/stampo”

**Effetto attuale:** la persona deve capire prima la struttura del software, poi lavorare. Dovrebbe essere il contrario.

### 3.2 Contrasto e leggibilità non affidabili

Nel tema attuale convivono:

- testi con opacità basse,
- superfici traslucide multiple,
- gradienti e overlay,
- font definiti in modo non pienamente coerente.

Risultato: alcune informazioni secondarie diventano difficili da leggere, specialmente su monitor cucina non calibrati, tablet economici, o ambienti con luce forte.

### 3.3 Complessità interattiva troppo alta

Il wizard è ricco ma denso:

- molte azioni in un singolo step,
- colonne multiple anche su viewport medie,
- nomenclatura “designer-like” (design/layout/checklist) più che “chef-like” (servizio/piatti/allergeni/stampa).

### 3.4 Feedback operativi deboli

Messaggi d’errore troppo generici (“inizializzazione/validazione/salvataggio falliti”) non aiutano a capire:

- cosa è andato storto,
- dove intervenire,
- come rientrare nel flusso.

### 3.5 Accessibilità e robustezza

Sono presenti elementi positivi (focus style), ma manca una strategia completa:

- controllo sistematico contrasto WCAG,
- gerarchia tipografica stabile,
- stati vuoti/error/loading con priorità operativa.

---

## 4) Root cause tecnica (perché succede)

1. **UI costruita per feature e non per task**: ottima copertura funzionale, ma journey operativo non orchestrato.
2. **Design system incompleto**: token presenti, ma uso non sempre coerente su componenti e stati.
3. **Validazione tardi nel funnel**: molte verifiche arrivano a fine percorso invece di prevenire errore step-by-step.
4. **Domain language poco aderente al ruolo chef**: lessico tecnico e navigazione “modulare” invece che orientata al servizio.

---

## 5) Piano di rilancio (90 giorni)

## Fase 0 — Stabilizzazione rapida (settimane 1-2)

**Obiettivo:** togliere subito frizione evidente.

- Definire **palette accessibile minima** (testo primario/secondario, superfici, CTA) con target WCAG AA.
- Ridurre opacità aggressive e overlay nei layer principali.
- Uniformare tipografia, spacing e gerarchia titoli/campi.
- Sostituire copy tecnico con copy operativo (“Servizio”, “Piatti selezionati”, “Pronto per stampa”).
- Introdurre errori espliciti e azionabili (“Seleziona struttura”, “Inserisci nome menu”, ecc.).

**Deliverable:** UI hardening patch + checklist contrasto + microcopy pack.

## Fase 1 — Flusso Chef-first (settimane 3-6)

**Obiettivo:** ridurre complessità percepita del 40-50%.

- Nuovo percorso unico “**Crea menu servizio**” in 4 step reali:
  1. Contesto servizio (struttura, data, turno)
  2. Composizione (piatti suggeriti + ricerca)
  3. Controlli (allergeni, coperture categorie, note)
  4. Output (anteprima, pubblica, stampa)
- Rendere secondarie (non primarie) sezioni tecniche come layout avanzato e cataloghi.
- Validazione progressiva per step con blocco intelligente del “Prosegui”.
- Salvataggio bozza automatico e ripresa sessione.

**Deliverable:** nuovo wizard task-based + metriche funnel per step.

## Fase 2 — Affidabilità operativa (settimane 7-10)

**Obiettivo:** eliminare interruzioni e ambiguità.

- Standardizzare stato schermate: loading/success/error/empty.
- Introdurre pannello “Problemi da risolvere” con link diretto al campo.
- Migliorare resilienza API lato UI (retry controllato, timeout messaging, fallback).
- Distinguere chiaramente “bozza”, “pubblicabile”, “pubblicato”.

**Deliverable:** framework stati UI + error model condiviso FE/BE.

## Fase 3 — Adozione e scalabilità (settimane 11-13)

**Obiettivo:** aumentare adozione reale da parte degli chef.

- Onboarding guidato in-app (3 minuti, role-based).
- Template preimpostati per scenario (colazione, pranzo, cena, evento).
- Libreria “piatti più usati” + suggerimenti contestuali leggeri.
- Telemetria UX (abbandono step, tempo medio creazione, errori ricorrenti).

**Deliverable:** onboarding + template pack + dashboard KPI prodotto.

---

## 6) KPI di successo (misurabili)

- **Time-to-first-menu pubblicabile**: target -50%.
- **Tasso completamento wizard**: target > 75%.
- **Errori bloccanti per sessione**: target -60%.
- **Richieste supporto sul modulo menu**: target -40% in 60 giorni.
- **Soddisfazione utenti chef (CSAT interno)**: target ≥ 4/5.

---

## 7) Priorità immediate consigliate (questa settimana)

1. Audit contrasto e tipografia sulle schermate principali.
2. Revisione microcopy orientata al linguaggio cucina.
3. Definizione journey unico “Crea menu servizio”.
4. Error handling “actionable” per validazione e salvataggio.
5. Test rapidi con 3 chef reali (30 minuti ciascuno, task osservati).

---

## 8) Rischi e mitigazioni

- **Rischio:** redesign estetico senza impatto operativo.  
  **Mitigazione:** KPI di task completion come criterio di accettazione.

- **Rischio:** regressioni funzionali durante refactor UI.  
  **Mitigazione:** rollout progressivo con feature flag e test su percorso critico.

- **Rischio:** sovraccarico roadmap con feature “nice-to-have”.  
  **Mitigazione:** priorità assoluta a completamento menu + pubblicazione.

---

## 9) Decisione proposta

Procedere con approccio **“UX rescue + task orchestration”**:

- mantenere backend e modelli,
- ricentrare frontend sui task degli chef,
- adottare standard accessibilità/leggibilità come requisito non negoziabile,
- misurare il successo con KPI di uso reale.

Questo massimizza il valore della tecnologia già costruita e trasforma lo strumento in un prodotto realmente utilizzabile in cucina.
