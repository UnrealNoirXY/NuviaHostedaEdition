# Menu Creation Studio - Analisi Strategica V2

## 1. Stato Attuale: "Dove siamo"
Il Menu Creation Studio ha completato con successo la sua fase di "Desktop Publishing". Attualmente è uno strumento solido per:
*   Composizione visiva dei menu (Drag & Drop).
*   Gestione base degli allergeni e della stagionalità.
*   Generazione automatizzata di documenti (PDF, Word, Cavalieri).
*   Governance e versioning.

**Il limite:** Lo strumento è percepito come "banale" dagli utenti Chef perché manca la dimensione economica e tecnica della ricetta. Gli ingredienti sono semplici etichette di testo senza peso né valore.

## 2. La Visione "Chef-First": Dallo Stile alla Sostanza
L'obiettivo della Fase 2 è trasformare lo Studio in un **Assistente Operativo e Finanziario**. Non più solo "cosa scriviamo nel menu", ma "quanto ci costa servirlo".

### Pilastri della Nuova Architettura
1.  **Ricetta Tecnica (Engineering):** Ogni piatto passa da "lista di nomi" a "distinta base". Inserimento di quantità, unità di misura e calcolo dello scarto (lordo vs netto).
2.  **Food Cost in Tempo Reale:** Integrazione nativa con il modulo **Economato**. Il costo di ogni piatto viene ricalcolato dinamicamente basandosi sull'ultimo prezzo di acquisto registrato per la specifica struttura.
3.  **Margine di Contribuzione:** Dashboard immediata nell'editor che mostra il Food Cost % e il margine lordo rispetto al prezzo di vendita.
4.  **Governance Finanziaria:** Alert automatici ("Food Cost troppo alto") e suggerimenti di ottimizzazione (es. "Sostituisci ingrediente fuori stagione con alternativa a minor costo").

## 3. Roadmap Tecnica di Implementazione

### Fase A: Potenziamento Modelli (Backend)
*   Introduzione del modello `PiattoIngrediente` (Relazione many-to-many con metadati: quantità, unità, scarto).
*   Mappatura tra `Ingrediente` e `EconomatoItem`.

### Fase B: Motore di Calcolo (API)
*   Endpoint per il calcolo del "Theoretical Food Cost" aggregato per menu e struttura.
*   Integrazione negli `Insights` della componente finanziaria.

### Fase C: Esperienza Utente (Frontend)
*   **Editor Ricetta Pro:** Nuova interfaccia per lo Chef per inserire dosi e pesi.
*   **Cost HUD:** Barra laterale sempre visibile con il costo in tempo reale durante la creazione del piatto.
*   **Menu Financial View:** Vista globale del menu con costo totale stimato e margine previsto.

## 4. Impatto Previsto
*   **Riduzione degli sprechi:** Consapevolezza immediata del costo piatto.
*   **Efficienza decisionale:** Lo Chef può decidere se cambiare un piatto in base al margine prima ancora di stamparlo.
*   **Integrazione Aziendale:** Connessione totale tra acquisti (Economato) e offerta (Menu).
