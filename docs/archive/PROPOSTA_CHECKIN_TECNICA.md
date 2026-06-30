# Proposta Tecnica e Piano di Sviluppo: Servizio di Check-in Online

Ciao, sono Jules. Dopo aver analizzato la struttura del tuo software esistente, ho preparato questa proposta tecnica dettagliata per l'implementazione del nuovo servizio di check-in online.

Questo documento unisce le idee funzionali con un piano di sviluppo concreto basato sulla configurazione attuale del tuo progetto Django.

---

### **1. Analisi del Sistema Esistente**

La mia esplorazione del codice ha rivelato un punto fondamentale per il successo del progetto:

*   **Il "Cuore" delle Prenotazioni è il Modello `Ticket`:** Il sistema non utilizza un modello `Booking` o `Prenotazione` dedicato. Invece, sfrutta un modello generico `Ticket` (all'interno dell'app `tickets`) per gestire quelle che, a tutti gli effetti, sono le prenotazioni dei resort.
*   **Mancanza di Campi Specifici:** Il modello `Ticket` attuale, pur essendo funzionale, non possiede campi essenziali per un processo di check-in, come:
    *   Data di check-in e check-out.
    *   Una struttura per memorizzare i dati anagrafici degli ospiti (oltre al creatore del ticket).
    *   Un sistema per archiviare i documenti d'identità.
    *   Uno stato per tracciare il completamento del check-in online.

Questa analisi è cruciale: qualsiasi sviluppo dovrà **estendere e arricchire il sistema `Ticket` esistente**, non sostituirlo.

---

### **2. Idee e Proposte Funzionali**

Le funzionalità proposte rimangono quelle delineate in precedenza, ma ora sono contestualizzate tecnicamente.

1.  **Portale di Check-in Self-Service:**
    *   Un'interfaccia web accessibile tramite un link sicuro e univoco inviato all'ospite (l'utente `created_by` del `Ticket`).
    *   L'ospite si autentica usando il numero del ticket e la sua email/cognome.

2.  **Inserimento Dati Ospiti:**
    *   Un form guidato per inserire i dati anagrafici di tutti gli ospiti associati a quella prenotazione (`Ticket`).

3.  **Caricamento Documenti:**
    *   Una sezione per caricare le foto o le scansioni dei documenti d'identità per ogni ospite. I file saranno archiviati in modo sicuro e associati al rispettivo ospite.

4.  **Firma Digitale e Pagamenti:**
    *   Accettazione delle condizioni del soggiorno e dell'informativa privacy.
    *   (Opzionale) Integrazione con un gateway di pagamento per saldare il soggiorno o le tasse turistiche.

5.  **Notifica di Completamento:**
    *   Sia l'ospite che lo staff della reception ricevono una notifica quando il check-in online è stato completato. Nel gestionale, il `Ticket` corrispondente verrà aggiornato con un nuovo stato (es. "Check-in Online Eseguito").

---

### **3. Piano di Sviluppo Tecnico**

Questo è il piano che propongo di seguire per implementare la soluzione in modo pulito e integrato.

**Fase 1: Estensione del Modello Dati (Backend)**

1.  **Creare una Nuova App `checkin`:** Per mantenere il codice organizzato e separato, tutte le nuove logiche risiederanno in una nuova app Django chiamata `checkin`.
2.  **Modificare il Modello `Ticket` Esistente:**
    *   Aggiungeremo i seguenti campi al file `tickets/models.py`, nel modello `Ticket`:
        ```python
        # Campi da aggiungere a tickets.models.Ticket
        check_in = models.DateTimeField(null=True, blank=True, verbose_name="Data Check-in")
        check_out = models.DateTimeField(null=True, blank=True, verbose_name="Data Check-out")
        online_checkin_status = models.CharField(max_length=20, default='pending', choices=[('pending', 'In attesa'), ('completed', 'Completato')])
        ```
3.  **Creare i Nuovi Modelli nell'app `checkin`:**
    *   Creeremo un file `checkin/models.py` con due nuovi modelli:
        *   **`Guest`**: Per i dati degli ospiti. Sarà collegato al `Ticket` tramite una `ForeignKey`.
            ```python
            # in checkin/models.py
            class Guest(models.Model):
                ticket = models.ForeignKey('tickets.Ticket', on_delete=models.CASCADE, related_name='guests')
                first_name = models.CharField(max_length=100)
                last_name = models.CharField(max_length=100)
                date_of_birth = models.DateField()
                # ... altri campi anagrafici
            ```
        *   **`GuestDocument`**: Per i documenti. Sarà collegato al `Guest`.
            ```python
            # in checkin/models.py
            class GuestDocument(models.Model):
                guest = models.OneToOneField(Guest, on_delete=models.CASCADE, related_name='document')
                document_image = models.ImageField(upload_to='guest_documents/')
                uploaded_at = models.DateTimeField(auto_now_add=True)
            ```
4.  **Creare e Applicare le Migrazioni:** Eseguiremo i comandi `makemigrations` e `migrate` per applicare queste modifiche al database.

**Fase 2: Sviluppo del Flusso di Check-in (Frontend & Backend)**

1.  **Creare le Viste (Views):** Nell'app `checkin`, svilupperemo le viste Django per gestire il processo a più passaggi (form wizard).
2.  **Creare i Template:** Progetteremo le pagine HTML (`templates`) con i form per l'inserimento dei dati e l'upload dei file.
3.  **Sviluppare la Logica di Salvataggio:** La logica che, al completamento del form, crea i record `Guest` e `GuestDocument` nel database e aggiorna lo stato del `Ticket`.

**Fase 3: Integrazione con il Pannello Admin**

1.  **Registrare i Nuovi Modelli:** Renderemo i modelli `Guest` e `GuestDocument` visibili e gestibili nel pannello di amministrazione (Django Admin).
2.  **Migliorare la Vista del Ticket:** Modificheremo la visualizzazione del `Ticket` nell'admin per:
    *   Mostrare i nuovi campi (`check_in`, `check_out`, `online_checkin_status`) come sola lettura.
    *   Visualizzare un elenco degli ospiti (`Guest`) associati direttamente nella pagina del ticket, con un link per vedere i loro documenti.

**Fase 4: Test e Rilascio**

1.  **Unit & Integration Testing:** Scriveremo test automatici per validare la nuova logica.
2.  **Test Manuale End-to-End:** Simuleremo l'intero processo dal punto di vista di un ospite per garantire che tutto funzioni correttamente.
3.  **Rilascio:** Una volta superati i test, il nuovo servizio sarà pronto per essere utilizzato.

---

Questo piano strutturato garantisce che il nuovo servizio di check-in si integri perfettamente con la logica di business esistente, fornendo al contempo una base solida e scalabile per future evoluzioni.

Sono pronto a procedere con la Fase 1 non appena mi darai il via libera.