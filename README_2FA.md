# Proposte per l'implementazione dell'Autenticazione a Due Fattori (2FA)

## Introduzione

Questo documento descrive diverse opzioni per implementare l'autenticazione a due fattori (2FA) nel progetto, al fine di aumentare la sicurezza degli account utente. Ogni opzione ha i suoi vantaggi e svantaggi in termini di sicurezza, usabilità e costi di implementazione.

## Opzione 1: Time-Based One-Time Password (TOTP)

Questa è la soluzione più comune e sicura per la 2FA. L'utente utilizza un'app di autenticazione (come Google Authenticator, Authy, o simili) per generare un codice a tempo che deve essere inserito dopo la password.

### Vantaggi
*   **Alta sicurezza**: I codici sono generati localmente sul dispositivo dell'utente e cambiano ogni 30-60 secondi.
*   **Standard de-facto**: Molti utenti hanno già familiarità con questo sistema.
*   **Nessun costo aggiuntivo**: Non dipende da servizi esterni per l'invio di codici (come SMS).
*   **Funziona offline**: L'utente può generare codici anche senza connessione a internet.

### Svantaggi
*   **Richiede un'app dedicata**: L'utente deve installare un'app di autenticazione sul proprio smartphone.

### Implementazione
L'implementazione può essere realizzata utilizzando la libreria `django-otp`. I passaggi principali sono:
1.  **Installazione**: Aggiungere `django-otp` e `qrcode` a `requirements.txt`.
2.  **Configurazione**: Aggiungere le app e il middleware necessari in `settings.py`.
3.  **Modifiche al modello Utente**: Aggiungere i campi necessari al modello `accounts.User` per memorizzare la configurazione 2FA di ogni utente.
4.  **Flusso di setup**: Creare una pagina nel profilo utente dove l'utente può abilitare la 2FA scansionando un QR code con la sua app di autenticazione.
5.  **Modifica della vista di login**:
    *   Dopo aver verificato username e password, il sistema non effettua subito il login.
    *   L'utente viene reindirizzato a una nuova pagina per inserire il codice TOTP.
    *   Solo dopo aver verificato il codice TOTP, l'utente viene autenticato.
6.  **Codici di recupero**: Generare dei codici di recupero monouso che l'utente può salvare e utilizzare in caso di perdita del dispositivo.

---

## Opzione 2: Codici via Email

In questa opzione, dopo aver inserito la password corretta, l'utente riceve un'email con un codice monouso da inserire per completare il login.

### Vantaggi
*   **Facilità d'uso**: Quasi tutti gli utenti hanno un indirizzo email e sanno come usarlo. Non sono richieste app aggiuntive.

### Svantaggi
*   **Sicurezza inferiore**: Se l'account email dell'utente è compromesso, anche la 2FA è compromessa.
*   **Dipendenza dal servizio email**: L'invio delle email potrebbe subire ritardi o fallire.
*   **Configurazione del server email**: Il progetto attualmente ha il backend email che stampa in console. Sarà necessario configurare un servizio SMTP affidabile (es. SendGrid, Amazon SES) per l'invio di email in produzione.

### Implementazione
Anche questa opzione può essere implementata con `django-otp` o con una soluzione personalizzata.
1.  **Configurazione SMTP**: Configurare il backend email in `settings.py` per utilizzare un servizio di invio email.
2.  **Modifica della vista di login**:
    *   Dopo la verifica della password, generare un codice casuale e inviarlo all'email dell'utente.
    *   Salvare il codice (o un suo hash) nella sessione dell'utente con una scadenza.
    *   Reindirizzare l'utente a una pagina per inserire il codice ricevuto.
3.  **Pagina di verifica**: Creare una pagina in cui l'utente inserisce il codice. Se il codice è corretto e non è scaduto, l'utente viene autenticato.

---

## Opzione 3: Codici via SMS

Simile all'opzione via email, ma il codice monouso viene inviato tramite messaggio SMS al numero di telefono dell'utente.

### Vantaggi
*   **Molto conveniente**: La maggior parte degli utenti ha uno smartphone e può ricevere SMS.

### Svantaggi
*   **Costi**: L'invio di SMS richiede l'integrazione con un gateway SMS a pagamento (es. Twilio, Vonage).
*   **Sicurezza**: Gli SMS possono essere intercettati (tramite SIM swapping o altre tecniche), rendendo questa opzione meno sicura di TOTP.
*   **Dipendenza dalla rete mobile**: La consegna degli SMS può subire ritardi.

### Implementazione
1.  **Aggiungere campo telefono**: Aggiungere un campo `phone_number` al modello `accounts.User` e un modo per l'utente di verificarlo.
2.  **Integrazione Gateway SMS**: Scegliere un provider SMS e integrare la sua API nel progetto.
3.  **Modifica della vista di login**:
    *   Dopo la verifica della password, inviare il codice via SMS al numero di telefono dell'utente.
    *   Reindirizzare a una pagina di verifica.
4.  **Pagina di verifica**: Simile al flusso via email.

---

## Raccomandazione

Si consiglia di implementare l'opzione **TOTP (Opzione 1)** come metodo principale di 2FA. È la soluzione più sicura e non comporta costi ricorrenti. Per migliorare l'esperienza utente, si potrebbe offrire l'**Email (Opzione 2)** come metodo di recupero dell'account o come alternativa per gli utenti che non desiderano utilizzare un'app di autenticazione, tenendo presente la necessità di configurare un servizio di invio email affidabile.

L'opzione SMS è potente ma introduce costi e complessità aggiuntive che potrebbero non essere necessarie se gli altri due metodi sono disponibili.

## Prossimi Passi

1.  **Decisione**: Scegliere quale o quali metodi di 2FA implementare.
2.  **Piano di sviluppo**: Creare un piano dettagliato per l'implementazione della soluzione scelta.
3.  **Implementazione**: Scrivere il codice, i test e la documentazione necessari.
4.  **Rilascio**: Comunicare agli utenti la nuova funzionalità e guidarli nel processo di attivazione.
