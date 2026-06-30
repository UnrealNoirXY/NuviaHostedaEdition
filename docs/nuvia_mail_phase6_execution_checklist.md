# Nuvia Mail — Fase 6 Execution Checklist

## Obiettivo
Chiudere i gap tra MVP operativo attuale e target enterprise del blueprint, con priorità su provider reali, sicurezza credenziali/token, inbox read-only e delta sync.

## Scope
- Provider adapters: Google Workspace, Microsoft 365, IMAP standard.
- OAuth2 flow completo (auth code + refresh token).
- Inbox sync read-only con threading.
- Security hardening su segreti e audit trail.
- API dedicate `/api/nuvia-mail/*`.

## Milestone 1 — Provider foundation
- [ ] Definire interfaccia `ProviderAdapter` con metodi minimi:
  - `authorize_url()`, `exchange_code()`, `refresh_access_token()`
  - `send_message()`
  - `list_folders()`, `list_messages_delta()`, `get_message()`
- [ ] Implementare `GoogleAdapter` (Gmail API).
- [ ] Implementare `MicrosoftAdapter` (Graph Mail).
- [ ] Implementare `ImapAdapter` (IMAP IDLE opzionale, polling baseline).
- [ ] Aggiungere mapping errori provider → errori interni tipizzati.

## Milestone 2 — OAuth e segreti
- [ ] Persistenza token con cifratura applicativa forte.
- [ ] Rotazione e revoca token.
- [ ] Mascheramento segreti nei log.
- [ ] Audit eventi: connect/disconnect/refresh failure.
- [ ] Job periodico di refresh proattivo token in scadenza.

## Milestone 3 — Inbox read-only e threading
- [ ] Nuove entità DB:
  - `MailFolder`
  - `MailThread`
  - `MailMessage`
  - `MailSyncCheckpoint`
- [ ] Delta sync per provider con checkpoint per account/folder.
- [ ] Normalizzazione MIME (plain/html, allegati metadata-only in fase iniziale).
- [ ] Threading tramite message-id, references, in-reply-to.
- [ ] Endpoint read-only inbox/thread detail.

## Milestone 4 — API e UX operativa
- [ ] API REST dedicate:
  - `POST /api/nuvia-mail/accounts/connect`
  - `POST /api/nuvia-mail/accounts/{id}/test`
  - `GET /api/nuvia-mail/folders`
  - `GET /api/nuvia-mail/threads`
  - `GET /api/nuvia-mail/threads/{id}`
  - `POST /api/nuvia-mail/queue`
  - `POST /api/nuvia-mail/queue/process`
- [ ] Aggiornare la landing per consumare endpoint API gradualmente.
- [ ] Migliorare stati UI per errori provider e retry guidato.

## Milestone 5 — Compliance & Security hardening
- [ ] Policy DLP avanzata (regex, classificatori, scoring rischio).
- [ ] Allowlist/denylist destinatari per tenant.
- [ ] Rule engine per blocco/quarantine/approval.
- [ ] Export audit trail firmato per compliance.

## Milestone 6 — Qualità, SRE e rollout
- [ ] Test contract per adapter provider.
- [ ] Test end-to-end onboarding OAuth + send + sync.
- [ ] Metriche: send latency, sync lag, refresh failures, bounce ratio.
- [ ] Alerting operativo e dashboard.
- [ ] Rollout progressive:
  - canary tenants
  - feature flags per provider
  - fallback su send queue esistente

## Definition of Done
- [ ] Almeno 2 provider OAuth in produzione (Google + Microsoft).
- [ ] Inbox read-only disponibile con delta sync stabile.
- [ ] Nessun segreto in chiaro in DB/log.
- [ ] SLA operativo definito e monitorato.
- [ ] Documentazione runbook incident/rotation completata.
