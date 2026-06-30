# Istruzioni di Deployment su Server Ubuntu

Questa guida fornisce tutti i passaggi per configurare il progetto, includendo la nuova `Home Desk` basata su React.

## Sequenza di Comandi Fondamentale (per Aggiornamenti)

Se stai aggiornando il codice su un server già configurato, la sequenza corretta di comandi da eseguire (come utente **non-root**, es. `deploy`) è sempre la seguente:

```bash
# 1. Aggiorna il codice dal repository
git pull

# 2. Aggiorna le dipendenze Python (se requirements.txt è cambiato)
pip install -r requirements.txt

# 3. Aggiorna le dipendenze e ricompila il frontend
cd frontend
yarn install
yarn build
cd ..

# 4. Raccogli i file statici per Django
python manage.py collectstatic --noinput

# 5. Applica le migrazioni del database
python manage.py migrate

# 6. Riavvia il server
sudo systemctl restart gunicorn
sudo systemctl reload nginx
```

> **Nota PWA/Cache**: dopo aver ricompilato il frontend e riavviato i servizi, se il browser continua a mostrare la versione vecch
ia delle pagine (es. manutenzione non responsive), esegui un hard refresh (Ctrl+F5 / Cmd+Shift+R) o cancella l’eventuale service
 worker dal pannello "Applicazione" degli strumenti di sviluppo. I client mobili in particolare possono mantenere in cache gli a
sset precedenti finché non viene aggiornato il service worker.

---

## Troubleshooting: Pagina Bianca / Widget non Visibili

Se dopo aver seguito tutti i passaggi la pagina `/desk` si carica ma mostra solo il titolo "Home Desk" senza i widget e senza errori nella console del browser, il problema è quasi certamente legato ai **permessi dei file**.

Questo accade se i comandi di build del frontend (`yarn build` o `npm run build`) vengono eseguiti come utente `root`. I file generati apparterranno a `root` e il server web (che gira con un altro utente, es. `www-data` o `deploy`) non avrà il permesso di leggerli, causando un fallimento silenzioso.

**Per risolvere, segui questa checklist definitiva nell'ordine esatto:**

1.  **Assumi la proprietà dei file**: Dalla cartella principale del progetto (es. `/home/deploy/manutenzionetest`), esegui questo comando per assicurarti che il tuo utente non-root (es. `deploy`) sia proprietario di tutto:
    ```bash
    sudo chown -R deploy:deploy .
    ```
    *(Sostituisci `deploy:deploy` con `tuoutente:tuoutente` se necessario)*

2.  **Esegui i comandi come utente non-root**: Assicurati di eseguire tutti i comandi seguenti come utente `deploy`, **non** come `root`, seguendo la sequenza del punto precedente.

3.  **Riavvia i servizi** e **pulisci la cache del browser** (`Ctrl+Shift+R`).

---

## Installazione Iniziale da Zero

### 1. Prerequisiti di Sistema (Ubuntu)

```bash
sudo apt update
sudo apt install -y python3-pip python3-venv nodejs npm
# Installa Yarn globalmente
sudo npm install -g yarn
```

### 2. Configurazione Progetto

```bash
# Clona il repository
git clone <URL_DEL_TUO_REPOSITORY>
cd <NOME_DELLA_CARTELLA_PROGETTO>

# Crea e attiva l'ambiente virtuale
python3 -m venv venv
source venv/bin/activate
```

### 3. Installazione Dipendenze

```bash
# Backend
pip install -r requirements.txt

# Frontend
cd frontend
yarn install
cd ..
```

### 4. Configurazione Finale e Primo Avvio

```bash
# Crea e compila il file .env con le tue configurazioni
# Esempio: nano .env
# SECRET_KEY=...
# DEBUG=False
# ALLOWED_HOSTS=...
# DATABASE_URL=...

# Compila gli asset per la produzione
cd frontend
yarn build
cd ..

# Raccogli tutti i file statici
python manage.py collectstatic --noinput

# Esegui le migrazioni del database
python manage.py migrate

# Avvia il server (esempio, vedi gunicorn.service per la configurazione systemd)
gunicorn --workers 3 --bind 0.0.0.0:8000 gestione_manutenzioni.wsgi:application
```

---
## Stato Attuale della Funzionalità: Home Desk

Questa implementazione della nuova Home Desk in React è una **base di partenza**. La struttura (backend API, frontend React, build system) è completa e funzionante.

Tuttavia, per accelerare lo sviluppo e risolvere i problemi di configurazione, **non tutti i widget della vecchia dashboard sono stati reimplementati**.

*   **Widget Funzionanti**: Annunci, Panoramica Ticket, Grafico Recensioni.
*   **Widget Placeholder**: Tutti gli altri widget appariranno come dei "placeholder" con la dicitura "in fase di sviluppo".

Questo fornisce una solida base su cui potrai (o potrò) costruire i widget rimanenti in futuro, seguendo il pattern già stabilito.

### Variabili ambiente per Menu Creation Studio
- `CELERY_BROKER_URL` (es. `redis://127.0.0.1:6379/0`) e, opzionale, `CELERY_TASK_DEFAULT_QUEUE` per i worker Celery.
- `MENU_DOCUMENT_RETENTION_DAYS` (default 7) e `MENU_DOCUMENT_MAX_AGE_DAYS` (default 30) per la durata dei file esportati.
- `DJANGO_VITE_DEV_MODE`: imposta `false` in ambienti dove non è in esecuzione il dev server Vite (altrimenti Django tenterà di
  caricare `http://localhost:5173/vite/src/main.css`). Abilita solo in locale quando usi `yarn dev`.
