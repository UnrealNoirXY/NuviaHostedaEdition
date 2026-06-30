# Proposta per il nuovo strumento "Procedure" (Versione 2)

Questo documento descrive il piano di sviluppo, le idee e le proposte per l'implementazione del nuovo strumento "Procedure" all'interno della piattaforma "Noir". **Questa versione del documento è stata aggiornata per includere i nuovi requisiti discussi.**

---

## 1. Analisi e Filosofia di Progetto

Dopo aver analizzato la struttura esistente della piattaforma, in particolare l'applicazione `documents`, la proposta si basa su un approccio di **integrazione coerente** piuttosto che sulla creazione di un sistema completamente nuovo e isolato.

**Principi Guida:**

*   **Modularità**: Lo strumento verrà sviluppato come una nuova app Django dedicata, chiamata `procedures`, per mantenere il codice organizzato e seguire la convenzione del progetto.
*   **Riuso del Codice**: Sfrutteremo i componenti e le logiche esistenti (es. sistema di ruoli, gestione degli accessi, template di base) per accelerare lo sviluppo e garantire coerenza.
*   **Esperienza Utente (UX)**: L'interfaccia sarà pulita, intuitiva e si integrerà perfettamente con il tema grafico esistente della piattaforma.

---

## 2. Idee e Funzionalità Proposte

### Funzionalità di Base (MVP - Minimum Viable Product)

1.  **Upload e Aggiornamento Procedure**:
    *   Gli utenti con ruolo `Superadmin` o `Owner` avranno accesso a un'interfaccia per caricare e **aggiornare** i documenti di procedura in formato PDF.
    *   Durante il caricamento, l'amministratore dovrà associare la procedura a uno o più "settori" (corrispondenti ai ruoli utente).

2.  **Visualizzazione PDF Integrata (In-App)**:
    *   Gli utenti potranno visualizzare i PDF **direttamente all'interno dell'applicazione** in una vista dedicata o in una finestra modale, senza dover scaricare il file o aprire una nuova scheda del browser.

3.  **Gestione delle Versioni e Date**:
    *   Ogni procedura mostrerà la **data dell'ultimo aggiornamento** in un formato "elegante" e leggibile (es. "Aggiornato il 12 Settembre 2025").
    *   Quando un file viene aggiornato, la data si aggiorna automaticamente e un **disclaimer "Nuova Versione"** apparirà accanto alla procedura per notificare il cambiamento.

4.  **Integrazione nell'Hub Principale**:
    *   Nella dashboard principale (Hub), verrà aggiunta una nuova "card" per l'accesso rapido alla sezione "Procedure".
    *   Questa card avrà un'**icona pertinente** (es. un libro o un documento) e uno **schema di colori unico** ma in linea con il design della piattaforma, per renderla immediatamente riconoscibile.

5.  **Accesso Basato sul Ruolo**:
    *   Ogni utente visualizzerà unicamente le procedure pertinenti al proprio ruolo/settore.
    *   Gli amministratori avranno una vista completa di tutte le procedure.

### Funzionalità Avanzate (Proposte per evoluzioni future)

*   **Storico Versioni**: Oltre a indicare l'ultima versione, permettere di accedere e visualizzare le versioni precedenti di una procedura.
*   **Conferma di Lettura**: Tracciare quali utenti hanno visualizzato una specifica versione di una procedura.
*   **Ricerca Full-Text**: Indicizzare il contenuto dei PDF per una ricerca interna più potente.
*   **Notifiche Proattive**: Inviare una notifica agli utenti quando una procedura rilevante per loro viene aggiunta o aggiornata.

---

## 3. Piano di Sviluppo Dettagliato (Revisionato)

**Passo 1: Creazione della Nuova App `procedures`**
*   (Invariato) Eseguire `django-admin startapp procedures` e aggiungerla a `INSTALLED_APPS`.

**Passo 2: Definizione del Modello Dati (Revisionato)**
*   Creare il modello `Procedure` in `procedures/models.py` con i seguenti campi:
    *   `title`: `CharField`
    *   `file`: `FileField`
    *   `sectors`: `CharField` con `choices` o `ManyToManyField` ai ruoli.
    *   `uploaded_by`: `ForeignKey` a `User`.
    *   `created_at`: `DateTimeField(auto_now_add=True)` per memorizzare la data di creazione originale.
    *   `updated_at`: `DateTimeField(auto_now=True)` per tracciare l'ultima modifica.
    *   `version`: `IntegerField(default=1)` per tenere traccia del numero di versione.
*   Eseguire `makemigrations` e `migrate`.

**Passo 3: Creazione dei Form**
*   (Invariato) Sviluppare un `ProcedureForm` per l'upload e la modifica.

**Passo 4: Sviluppo delle Viste (Views) (Revisionato)**
*   `procedure_list_view`: Logica di filtraggio per ruolo utente.
*   `procedure_upload_view`: Gestirà la creazione di nuove procedure.
*   `procedure_update_view`: Una nuova vista per la gestione dell'aggiornamento di una procedura esistente. Questa vista **incrementerà il campo `version`** e sostituirà il file.
*   `procedure_viewer_view`: Una nuova vista che mostrerà il template con il visualizzatore PDF integrato.

**Passo 5: Creazione dei Template HTML (Revisionato)**
*   `procedure_list.html`:
    *   Dovrà includere la logica per visualizzare la data formattata (usando `django.contrib.humanize` o un filtro custom).
    *   Dovrà mostrare il disclaimer "Nuova Versione" se `procedure.version > 1`.
*   `procedure_form.html`: (Invariato)
*   `procedure_viewer.html`: **Nuovo template**. Conterrà un'area per la visualizzazione del PDF, utilizzando una libreria come **PDF.js** o un tag `<embed>`/`<iframe>` per una soluzione più semplice.

**Passo 6: Configurazione delle URL (Revisionato)**
*   Aggiornare `procedures/urls.py` per includere le nuove viste (`update` e `viewer`).

**Passo 7: Integrazione nell'Interfaccia Utente (Revisionato e Dettagliato)**
*   **Menu Laterale**: (Invariato) Aggiungere il link in `_sidebar.html`.
*   **Hub Dashboard**:
    *   Modificare il file `core/templates/core/hub.html`.
    *   Aggiungere un nuovo blocco `<div>` per la card "Procedure", seguendo la struttura delle card esistenti.
    *   Creare una nuova classe CSS (es. `.hub-card-procedures`) in un file CSS appropriato (es. `theme.css`) per definire il colore di sfondo/bordo unico.
    *   Scegliere un'icona da una libreria esistente nel progetto (es. Font Awesome) e aggiungerla alla card.

---

## 4. Conclusioni

(Invariato) Questo piano delinea un percorso chiaro per sviluppare uno strumento "Procedure" robusto e ben integrato. Partendo da una versione MVP, possiamo fornire rapidamente valore agli utenti, con la possibilità di arricchire lo strumento con funzionalità avanzate in futuro. L'approccio modulare garantisce che la piattaforma rimanga manutenibile e scalabile.
