import os
from celery import Celery
import environ

# Imposta il modulo di settings di Django per il programma 'celery'.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestione_manutenzioni.settings')

# --- Caricamento esplicito del file .env ---
# Questo è il passaggio chiave per garantire che Celery legga le variabili d'ambiente.
# In questo modo, anche se avviato come servizio, Celery conoscerà le credenziali.
env = environ.Env()
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env_file = os.path.join(BASE_DIR, '.env')
if os.path.exists(env_file):
    environ.Env.read_env(env_file)
# ---------------------------------------------

app = Celery('gestione_manutenzioni')

# Usa una stringa qui per evitare la serializzazione dell'oggetto di configurazione.
# Il namespace 'CELERY' significa che tutte le chiavi di configurazione di Celery
# devono avere il prefisso `CELERY_`.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Carica i moduli dei task da tutte le app Django registrate.
app.autodiscover_tasks()