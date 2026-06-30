#!/bin/bash

# Lo script si interrompe immediatamente se un comando fallisce.
set -e

# --- CONFIGURAZIONE (DA MODIFICARE PRIMA DELL'ESECUZIONE) ---
# Il nome utente che eseguirà l'applicazione sul server.
# IMPORTANTE: Esegui questo script come un utente con privilegi 'sudo'.
# Sostituisci 'ubuntu' con il tuo nome utente effettivo sul VPS se è diverso.
APP_USER="Noir"

# Il nome del tuo progetto Django (la cartella che contiene settings.py).
PROJECT_NAME="NoirToolsKit"

# Il tuo nome di dominio. SOSTITUISCI QUESTO VALORE!
DOMAIN="72.60.36.75"
# --- FINE CONFIGURAZIONE ---


echo "--- Avvio dello script di deploy ---"

# Questo script presume che tu abbia già caricato i file del progetto sul server
# e che lo stia eseguendo dalla cartella principale del progetto.
PROJECT_ROOT_PATH=$(pwd)
echo "--- Percorso del progetto: $PROJECT_ROOT_PATH ---"

# --- 1. Aggiornamento del sistema e installazione delle dipendenze ---
echo "--- Aggiornamento del sistema e installazione delle dipendenze... ---"
sudo apt-get update
sudo apt-get install -y python3-pip python3-dev python3-venv nginx curl libmysqlclient-dev

# --- 2. Setup dell'ambiente Python ---
if [ ! -d "venv" ]; then
    echo "--- Creazione dell'ambiente virtuale Python... ---"
    python3 -m venv venv
fi

echo "--- Attivazione dell'ambiente virtuale e installazione dei pacchetti... ---"
source venv/bin/activate
pip install -r requirements.txt
deactivate

# --- 3. Setup di Django ---
echo "--- Esecuzione dei comandi di Django (collectstatic, migrate)... ---"
source venv/bin/activate
# Raccoglie tutti i file statici in un'unica cartella.
python manage.py collectstatic --noinput
# Applica le migrazioni al database.
# IMPORTANTE: Assicurati che il database sia già stato creato e che le variabili
# d'ambiente (DB_NAME, DB_USER, etc.) siano state impostate correttamente.
python manage.py migrate --noinput
deactivate

# --- 4. Setup di Gunicorn ---
# Questo passo presume che un file 'gunicorn.service' esista nella cartella del progetto.
echo "--- Configurazione del servizio Gunicorn (systemd)... ---"
# Sostituisce i segnaposto nel file di servizio con i valori corretti.
sed -i "s|PLACEHOLDER_USER|$APP_USER|g" gunicorn.service
sed -i "s|PLACEHOLDER_PROJECT_ROOT_PATH|$PROJECT_ROOT_PATH|g" gunicorn.service
sed -i "s|PLACEHOLDER_PROJECT_NAME|$PROJECT_NAME|g" gunicorn.service

sudo cp gunicorn.service /etc/systemd/system/gunicorn.service
sudo systemctl daemon-reload
sudo systemctl start gunicorn
sudo systemctl enable gunicorn # Abilita l'avvio automatico al boot.

echo "--- Gunicorn è stato avviato e abilitato. Controlla lo stato con: sudo systemctl status gunicorn ---"

# --- 5. Setup di Nginx ---
# Questo passo presume che un file 'nginx.conf' esista nella cartella del progetto.
echo "--- Configurazione di Nginx come reverse proxy... ---"
# Sostituisce i segnaposto nel file di configurazione di Nginx.
sed -i "s/PLACEHOLDER_DOMAIN/$DOMAIN/g" nginx.conf
sed -i "s|PLACEHOLDER_PROJECT_ROOT_PATH|$PROJECT_ROOT_PATH|g" nginx.conf

sudo cp nginx.conf /etc/nginx/sites-available/$PROJECT_NAME
# Rimuove la configurazione di default e abilita quella nuova.
if [ -f "/etc/nginx/sites-enabled/default" ]; then
    sudo rm /etc/nginx/sites-enabled/default
fi
if [ -L "/etc/nginx/sites-enabled/$PROJECT_NAME" ]; then
    sudo rm /etc/nginx/sites-enabled/$PROJECT_NAME
fi
sudo ln -s /etc/nginx/sites-available/$PROJECT_NAME /etc/nginx/sites-enabled/

# Testa la configurazione di Nginx e riavvia il servizio.
sudo nginx -t
sudo systemctl restart nginx

echo "--- Nginx è stato configurato. ---"
echo "--- DEPLOYMENT COMPLETATO! ---"
echo "--- Il tuo sito dovrebbe essere disponibile su http://$DOMAIN ---"
echo "--- RICORDA: Assicurati di aver impostato tutte le variabili d'ambiente richieste. ---"
echo "--- Potrebbe essere necessario un riavvio del server ('sudo reboot'). ---"
