# Proposta di Evoluzione della Home Desk (V2)

## 1. Introduzione

Dopo il successo della modernizzazione iniziale della Home Desk, questa proposta delinea la **Fase 2** di evoluzione. L'obiettivo è trasformare il calendario in uno strumento di collaborazione avanzato, arricchire l'ecosistema di widget con funzionalità più intelligenti e personalizzate, e integrare il tutto con il sistema di notifiche esistente.

---

## 2. Parte 1: Il Nuovo Calendario Collaborativo

Il calendario attuale verrà potenziato per diventare un hub per la pianificazione di team, ispirandosi all'usabilità di Google Calendar.

### 2.1. UI/UX Ispirata a Google Calendar

L'interfaccia del calendario sarà raffinata per un'esperienza utente superiore:
- **Viste Pulite:** Miglioreremo il rendering delle viste `mese`, `settimana` e `agenda` per una maggiore leggibilità.
- **Controlli Intuitivi:** Semplificheremo la navigazione tra le date e la creazione di eventi.
- **Stile Coerente:** Tutti gli elementi del calendario (bottoni, modali, eventi) seguiranno la nuova palette di colori e lo stile grafico della piattaforma.

### 2.2. Funzionalità Core: Inviti a Eventi e Task

Questa è la funzionalità principale della V2. Gli utenti potranno invitare colleghi a eventi e task, trasformando il calendario in uno strumento di pianificazione collaborativa.

#### Flusso Utente:
1.  Durante la creazione o modifica di un evento, l'utente vedrà un nuovo campo "Invita Colleghi".
2.  Cliccando, potrà cercare gli utenti a cui è autorizzato a inviare inviti.
3.  Una volta aggiunti, gli invitati riceveranno una notifica. L'evento apparirà nel loro calendario (inizialmente con uno stato "in attesa").

#### Permessi e Visibilità (Regole di Scope):
Per garantire la privacy e la corretta governance, il sistema di inviti seguirà regole di business precise:
-   Un **Superadmin** può invitare chiunque nella piattaforma.
-   Un **Proprietario (Owner)** può invitare solo gli utenti appartenenti alla sua stessa **società (Company)**.
-   Un **Direttore (Director)** può invitare solo gli utenti appartenenti al suo stesso **resort**.
-   Un **Capo Manutentore (Head Maintainer)** può invitare solo i **Manutentori (Maintainer)** del suo team/resort.
-   Altri ruoli, per default, non potranno inviare inviti, ma potranno essere invitati.

### 2.3. Personalizzazione: Sfondo del Calendario
Come richiesto, valuteremo l'applicazione dello sfondo scelto dall'utente nel suo profilo come sfondo del calendario. Questo verrà implementato con una tecnica che garantisca la piena leggibilità degli eventi (es. applicando un overlay semi-trasparente o un filtro blur).

---

## 3. Parte 2: Ecosistema di Notifiche Integrato

Per supportare la nuova funzionalità di invito, potenzieremo il sistema di notifiche.

### 3.1. Il Widget "Centro Notifiche"
Questo nuovo widget diventerà il cuore delle comunicazioni per l'utente sulla Home Desk.
- **Aggregazione:** Mostrerà non solo gli annunci, ma anche notifiche da altri moduli, a partire dagli inviti del calendario.
- **Interattività:** Ogni notifica di invito avrà azioni rapide come **"Accetta"** e **"Rifiuta"**.
    - Cliccando "Accetta", l'evento verrà confermato nel calendario dell'utente.
    - Cliccando "Rifiuta", l'organizzatore dell'evento riceverà una notifica.

### 3.2. Notifiche via Email
Sfruttando il sistema SMTP già configurato, ogni invito genererà anche una notifica via email.
- **Integrazione Esistente:** Utilizzeremo le funzionalità di invio email già presenti.
- **Stile Grafico Coerente:** Il template dell'email di invito sarà disegnato per essere perfettamente in linea con lo stile grafico delle altre comunicazioni della piattaforma (es. report, OTP, etc.), garantendo un'esperienza utente omogenea.

---

## 4. Parte 3: Evoluzione del Portafoglio Widget

Rinnoveremo la selezione di widget per massimizzare la rilevanza e l'utilità per ogni ruolo.

### 4.1. Widget da Ritirare
Come richiesto, i seguenti widget verranno rimossi dalle opzioni disponibili per ridurre il disordine e concentrarsi su informazioni più utili:
-   `Utenti Attivi`
-   `Stato del Sistema`

### 4.2. Proposte per Nuovi Widget
Ecco alcune idee per nuovi widget potenti e personalizzabili:

-   **Widget "Le Mie Attività Recenti"**: Una timeline personale che mostra le ultime azioni significative compiute dall'utente (es. "Hai chiuso il ticket #451", "Hai commentato l'annuncio 'Nuove Procedure'"). Permette di ritrovare facilmente il proprio lavoro.
-   **Widget "Azioni Rapide"**: Un pannello di bottoni configurabile dall'utente, che può aggiungere link diretti alle 3-5 pagine o azioni che usa più di frequente (es. "Crea Ticket", "Nuovo Ordine d'Acquisto", "Vedi Report Mensile").
-   **Widget "KPI Snapshot"**: Un widget compatto che mostra da 1 a 3 indicatori di performance chiave (KPI), specifici per il ruolo dell'utente. Esempi:
    - *Direttore*: Tasso occupazione, Punteggio medio recensioni.
    - *Capo Manutentore*: Tempo medio risoluzione ticket, N. ticket urgenti.
-   **Widget "Allerta Scorte Basse"**: Per i ruoli che gestiscono l'inventario (es. `Economo`), una lista degli articoli che sono al di sotto della soglia minima, con un link diretto per creare un ordine d'acquisto.

---

## 5. Prossimi Passi

Questa proposta delinea la visione per la Home Desk V2. Una volta approvata, procederò con la stesura di un piano di implementazione tecnico dettagliato per ogni funzionalità descritta.
