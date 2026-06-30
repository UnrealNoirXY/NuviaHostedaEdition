# Piano di Sviluppo: Piattaforma di Check-in Online Sicura

Questo documento traccia lo sviluppo della piattaforma di check-in online. Le attività completate sono state spuntate per mantenere una cronologia chiara dei progressi.

---

### **Fase 1: Fondamenta Sicure e Modelli Dati Avanzati**

- [x] **1.1: Creazione App `bookings`**: Creare la struttura della nuova app Django `bookings` per isolare la logica.
- [x] **1.2: Definizione dei Modelli Dati**: Definire i modelli `Booking`, `CheckInProcess`, `Guest`, `GuestDocument`, e `Consent` in `bookings/models.py` con tutti i campi di sicurezza suggeriti (hash dei token, scadenze, campi di audit, ecc.).
- [x] **1.3: Integrazione dell'App**: Aggiungere la nuova app `bookings` alle `INSTALLED_APPS` nel file di settings e creare i file `apps.py` e `admin.py` di base.
- [x] **1.4: Implementazione Logica Token**: Creare le funzioni per la generazione e la verifica sicura dei token di accesso, salvando solo l'hash nel database. (Implementata nel modello `Booking`).
- [x] **1.5: Creazione e Applicazione delle Migrazioni**: Generare il file di migrazione iniziale per i nuovi modelli e applicarlo al database.
- [x] **1.6: Setup Sicurezza Base**: Configurare `noindex, nofollow` per le future pagine di check-in e definire una Content Security Policy (CSP) restrittiva di base. (Realizzato parzialmente con `noindex` nel template, la CSP verrà finalizzata in seguito).

### **Fase 2: Portale Ospite - UX Fluida, Sicurezza Ferrea**

- [x] **2.1: Sviluppo Wizard di Check-in**: Creare le viste e i template per il flusso guidato dell'ospite, con un'interfaccia moderna e con autosave.
- [x] **2.2: Implementazione Upload Sicuro**: Sviluppare la logica di upload asincrono dei documenti con una coda di processamento per la scansione antivirus e l'estrazione OCR.
- [x] **2.3: Implementazione Firma Elettronica Semplice (FES)**: Sviluppare la logica per la generazione del PDF di riepilogo e la creazione di un audit trail della firma legalmente valido.
- [x] **2.4: Implementazione Autenticazione "Step-Up"**: Creare il meccanismo di invio e verifica OTP via email per le azioni critiche (es. firma).
- [x] **2.5: Gestione Consensi**: Sviluppare l'interfaccia e la logica per tracciare i consensi granulari (T&C, Privacy) e il double opt-in per la newsletter.

### **Fase 3: Dashboard Staff - Efficienza e Controllo**

- [x] **3.1: Sviluppo Controllo degli Accessi (RBAC)**: Creare i modelli o la logica per la gestione di ruoli e permessi granulari per lo staff.
- [x] **3.2: Creazione Dashboard di Gestione**: Sviluppare l'interfaccia principale per lo staff con la lista delle prenotazioni, filtri avanzati e badge di stato.
- [x] **3.3: Creazione Vista di Dettaglio**: Sviluppare la pagina di dettaglio della prenotazione con il visualizzatore di documenti e il confronto tra dati OCR e dati inseriti.
- [x] **3.4: Implementazione Azioni Rapide**: Aggiungere i pulsanti per le azioni comuni dello staff (es. "Rigenera Token", "Blocca Accesso").
- [x] **3.5: Implementazione Audit Log**: Integrare la registrazione di ogni accesso o modifica ai dati sensibili.

### **Fase 4: Integrazione, Test e Rilascio**

- [x] **4.1: Connettore Booking Engine**: Sviluppare lo script di importazione per sincronizzare le prenotazioni dal booking engine esterno.
- [x] **4.2: Test Funzionali e di Sicurezza**: Eseguire test approfonditi su tutto il flusso, inclusi tentativi di accesso non autorizzato e validazione dei permessi.
- [x] **4.3: Sviluppo Procedure di Conformità GDPR**: Preparare gli endpoint per gestire le richieste di accesso (DSAR) e cancellazione dei dati.
- [ ] **4.4: Rilascio Finale**: Mettere in produzione la piattaforma.