# Istruzioni per la Configurazione delle Notifiche

Questo documento spiega come attivare e configurare le notifiche via email per la piattaforma.

## 1. Tipi di Notifiche

La piattaforma supporta due tipi di notifiche:

*   **Notifiche Locali (già attive):** Sono le notifiche che appaiono all'interno dell'applicazione, segnalate dall'icona a forma di campanella nella barra di navigazione. Questo sistema è già funzionante e non richiede configurazione.
*   **Notifiche via Email (da configurare):** Il codice per inviare email è già implementato, ma il sistema di invio deve essere configurato per un ambiente di produzione. Attualmente, le email vengono stampate nella console del server e non inviate realmente.

## 2. Come Attivare le Notifiche via Email

Per attivare l'invio di email reali, è necessario configurare un **servizio SMTP**. Questo può essere un servizio di terze parti specializzato (consigliato) o un account email standard.

**Servizi Consigliati:**
*   **SendGrid:** Offre un piano gratuito generoso, è affidabile e facile da configurare.
*   **Mailgun:** Un'altra ottima alternativa con piani flessibili.
*   **Amazon SES:** Potente e scalabile, si integra bene se si utilizza l'infrastruttura AWS.

### 3. Passaggi di Configurazione

La configurazione avviene tramite **variabili d'ambiente** per garantire la sicurezza delle credenziali. Non scrivere mai password o chiavi API direttamente nel file `settings.py`.

Il file `settings.py` è già predisposto per leggere queste variabili. Ecco le variabili che devi impostare nel tuo ambiente di produzione (es. nel pannello di controllo di Hostinger, Vercel, o nel tuo file `.env` se usi `django-environ`):

1.  **EMAIL_BACKEND**
    *   **Valore:** `django.core.mail.backends.smtp.EmailBackend`
    *   *Questo dice a Django di usare un vero server SMTP invece della console.*

2.  **EMAIL_HOST**
    *   **Valore:** L'indirizzo del server SMTP del tuo provider (es. `smtp.sendgrid.net`).

3.  **EMAIL_PORT**
    *   **Valore:** La porta usata dal tuo provider (solitamente `587` per TLS o `465` per SSL).
    *   *Il valore `587` è il più comune.*

4.  **EMAIL_USE_TLS**
    *   **Valore:** `True`
    *   *Questo abilita la crittografia TLS, che è lo standard di sicurezza moderno. Impostalo a `False` solo se usi la porta `465` (SSL).*

5.  **EMAIL_HOST_USER**
    *   **Valore:** Il nome utente per l'autenticazione SMTP. Per SendGrid, questo è solitamente la stringa `apikey`. Per altri servizi, è il tuo nome utente.

6.  **EMAIL_HOST_PASSWORD**
    *   **Valore:** La tua password SMTP o, preferibilmente, una **API Key** generata dal tuo provider. L'uso di una API Key è più sicuro.

7.  **DEFAULT_FROM_EMAIL**
    *   **Valore:** L'indirizzo email da cui vuoi che le notifiche appaiano inviate (es. `notifiche@tuodominio.com`).

### Esempio di Configurazione (per SendGrid)

Se imposti queste variabili d'ambiente nel tuo server, il file `settings.py` dovrebbe essere modificato per leggerle in questo modo (questo pattern è già usato per `SECRET_KEY`, quindi puoi seguirlo):

```python
# in gestione_manutenzioni/settings.py

# ... altre impostazioni

# Impostazioni Email per Produzione
EMAIL_BACKEND = os.environ.get('EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = os.environ.get('EMAIL_HOST')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True').lower() in ['true', '1', 't']
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'webmaster@localhost')

# ... resto delle impostazioni
```
**Nota:** Ho aggiunto un fallback a `console.EmailBackend` e valori di default per sicurezza, così l'applicazione non si blocca se una variabile non è impostata. Dovrai aggiungere questo blocco di codice al tuo `settings.py`.

Una volta che hai impostato queste variabili d'ambiente sul tuo server di produzione, il sistema di notifiche email sarà pienamente operativo.
