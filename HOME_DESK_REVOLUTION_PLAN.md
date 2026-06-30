# Piano di Rivoluzione della Home Desk: "The Operational Cockpit"

## 1. Analisi dello Stato Attuale: "La Scrivania Vuota"
La Home Desk attuale è una promessa non mantenuta. Sebbene l'estetica sia moderna, manca di sostanza operativa:
- **Widget Placeholder:** Molti ruoli (Reception, Housekeeping, Economato) hanno dashboard piene di componenti "Coming Soon".
- **Dati Statici:** La timeline e la inbox mostrano numeri fittizi o parziali.
- **Assenza di Azione:** L'utente può solo "guardare" i dati, non può interagire con essi senza navigare in altre pagine.

---

## 2. La Visione: "Noir Operational Cockpit"
Trasformeremo la Home Desk da una dashboard passiva a un centro di comando attivo, adottando l'estetica **Noir Luxury** (vetro traslucido, gradienti profondi, accenti dorati/smeraldo).

### 2.1. Real-Time Timeline (Il Cuore Pulsante)
Sostituiremo gli eventi statici con un feed aggregato e filtrabile:
- **Aggregazione Polimorfica:** Un unico flusso per Ticket urgenti, Recensioni critiche, Ordini in attesa e Annunci.
- **Interattività:** Ogni evento avrà un tasto di risposta rapida (es. "Assegna a me" su un nuovo ticket).

### 2.2. Quick Actions (Il Braccio Operativo)
Ogni widget includerà 1 o 2 "Azioni Rapide" per ridurre i clic:
- **Manutenzione:** "Aggiorna Stato" (aperto -> in corso -> chiuso) con un tocco.
- **Reception:** "Fast Check-in" per gli arrivi del giorno.
- **Housekeeping:** "Segnala Guasto" pre-compilato con il numero della camera.
- **Owner:** "Approva Tutto" per ordini d'acquisto sotto una certa soglia.

### 2.3. Smart Focus Mode (La Mente Reattiva)
La modalità Focus non sarà più solo un tasto manuale, ma diventerà **Semantica**:
- **Trigger Automatici:** Se il sistema rileva un'anomalia (es. >3 ticket "Urgenti" in un'ora), la Home Desk attiva la Focus Mode autonomamente.
- **Adattamento Visivo:** I widget non critici vengono oscurati (dimmed), mentre quelli urgenti "pulsano" con bordi Crimson.
- **Focus Banner:** Un banner in alto spiega l'allerta e propone l'azione risolutiva principale.

---

## 3. Road Map di Implementazione (Senza Codice)

### Fase A: Consolidamento API (2 Settimane)
- Sviluppare gli endpoint mancanti per i widget di Reception, Housekeeping e Finance.
- Creare il "Timeline Aggregator" che interroga i diversi moduli del backend.

### Fase B: Design Noir & Quick Actions (3 Settimane)
- Implementazione del nuovo wrapper `NoirWidget` in React.
- Integrazione delle logiche di scrittura (POST) direttamente nei widget per le Quick Actions.

### Fase C: Smart Intelligence (2 Settimane)
- Sviluppo del motore di trigger per la Focus Mode automatica.
- Integrazione delle notifiche push PWA per gli alert critici della Focus Mode.

---

## 4. KPI di Successo
- **Abbattimento Clic:** Riduzione del 40% del tempo necessario per azioni comuni (es. assegnazione ticket).
- **Engagement Ruoli:** Dashboard 100% popolate per ogni dipendente, dal manutentore al direttore.
- **Reattività:** Riduzione del tempo medio di risposta agli alert critici grazie alla Smart Focus Mode.
