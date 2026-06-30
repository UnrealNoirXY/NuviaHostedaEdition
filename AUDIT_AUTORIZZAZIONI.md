# Audit del Sistema di Autorizzazioni - Lista degli Errori

A seguito di un'analisi approfondita del codice, sono state identificate le seguenti falle nella logica di autorizzazione e di visibilità dei dati. Questi errori consentono ad alcuni ruoli utente di accedere a dati al di fuori della loro area di competenza.

## Errore 1: Visibilità Totale delle Recensioni per i Direttori

*   **Applicazione Coinvolta:** `reviews`
*   **Viste Interessate:** `review_dashboard_view`, `review_list_view`
*   **Ruolo Interessato:** `Director`
*   **Descrizione del Problema:** Un utente con ruolo "Direttore", che dovrebbe essere limitato a un singolo resort, può attualmente visualizzare le recensioni di **tutti i resort** che appartengono alla stessa società.
*   **Causa Tecnica:** Le query in queste viste filtrano i dati in base a `user.company` invece che `user.resort` per il ruolo `Director`.

## Errore 2: Visibilità Totale dei Dati nel Cruscotto Direzione

*   **Applicazione Coinvolta:** `core`
*   **Vista Interessata:** `director_cockpit_view`
*   **Ruolo Interessato:** `Director`
*   **Descrizione del Problema:** Il "Cruscotto Direzione" mostra al Direttore i Key Performance Indicator (KPI) e i dati aggregati (Ticket Manutenzione, Ticket IT, Asset, Recensioni) per l'**intera società**, invece di limitare i calcoli al solo resort di competenza del direttore.
*   **Causa Tecnica:** Similmente all'errore 1, le query in questa vista usano `user.company` per filtrare i dati per un Direttore, portando a un'aggregazione di dati troppo ampia.

## Errore 3: Visibilità Totale dei Documenti per il Personale Amministrativo

*   **Applicazione Coinvolta:** `documents`
*   **Vista Interessata:** `document_list_view`
*   **Ruolo Interessato:** `Administrative`
*   **Descrizione del Problema:** Un utente con ruolo "Amministrativo" di una società può visualizzare i documenti caricati da utenti di **qualsiasi altra società** presente sulla piattaforma.
*   **Causa Tecnica:** La vista che elenca i documenti non applica alcun filtro basato sulla società dell'utente (`user.company`), restituendo tutti i documenti presenti nel database.
