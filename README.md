# Nuvia — Noir Tools Kit

Suite gestionale interna per hotel/resort. Monolite **Django 5.2** che raccoglie, in un
unico portale, gli strumenti operativi usati dallo staff: manutenzioni, prenotazioni e
check-in, HR e buste paga, analisi recensioni, finanza/economato, comunicazioni e altro.

> ℹ️ **Stato del progetto:** in consolidamento. È in corso un ridisegno strutturale guidato
> dal documento **[`PIANO_RIDISEGNO_MASTER.md`](./PIANO_RIDISEGNO_MASTER.md)** — leggilo prima
> di aggiungere nuove funzionalità.

## Stack

- **Backend:** Django 5.2, Django REST Framework, Channels (ASGI/WebSocket), Celery + Redis
  (task asincroni e schedulazione via `django-celery-beat`).
- **Database:** MySQL in produzione (via `PyMySQL`), SQLite in sviluppo.
- **Frontend:** `frontend/` — app **Vite + React 19** integrata nei template Django tramite
  `django-vite`. È **l'unico frontend supportato** (i precedenti esperimenti Next.js/React
  legacy sono stati rimossi).
- **Admin:** Django Admin con tema Jazzmin.

## Moduli principali (app Django)

| Area | App |
|---|---|
| Identità, hub, mail interna | `accounts`, `core` |
| Manutenzioni e ticket | `tickets`, `resort`, `assets` |
| Prenotazioni e check-in | `bookings` |
| HR e buste paga | `hr_portal` |
| Recensioni (analisi sentiment) | `reviews` |
| Finanza e magazzino | `financials`, `economato`, `purchase_orders`, `inventory` |
| Comunicazioni e notifiche | `communications`, `notifications` |
| Documenti e supporto | `documents`, `document_verification`, `it_support`, `procedures` |
| Menu Creation Studio | `menu_generator` |
| Altri strumenti | `competitors`, `svago`, `skills`, `profile_cards`, `desk` |

## Avvio in sviluppo

```bash
# 1. Backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # configura SECRET_KEY, DATABASE_URL, EMAIL_*, REDIS, ecc.
python manage.py migrate
python manage.py runserver

# 2. Frontend (in un secondo terminale)
cd frontend
yarn install
yarn dev            # dev server Vite
# in produzione: yarn build  (genera frontend/dist, servito via django-vite)
```

Per la configurazione completa delle variabili d'ambiente e del deploy vedi
[`DEPLOY_INSTRUCTIONS.md`](./DEPLOY_INSTRUCTIONS.md).

## Test

```bash
python manage.py test
```

## Documentazione

- **[`PIANO_RIDISEGNO_MASTER.md`](./PIANO_RIDISEGNO_MASTER.md)** — analisi e piano di ridisegno (fonte di verità).
- `docs/archive/` — proposte e analisi storiche dei singoli moduli (riferimento, non vincolanti).
