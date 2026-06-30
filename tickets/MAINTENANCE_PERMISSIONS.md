# Accesso strumento manutenzioni

Questa nota riassume l'intervento effettuato per sbloccare la creazione ticket da parte dei superadmin e serve come riferimento rapido su come funziona il controllo permessi dell'API manutenzioni.

## Cosa è stato cambiato
- **Estensione del gate di permesso**: il `TicketPermission` ora considera il ruolo `SUPERADMIN` tra quelli sempre abilitati all'API, anche senza il flag `has_maintenance_access`.
- **Allineamento della mappa permessi del calendario**: la funzione `_calendar_permission_map` usa la stessa logica, quindi i superadmin ottengono `canCreateTickets=True` senza flag aggiuntivi.
- **Copertura automatica**: è stato aggiunto un test API che autentica un utente `SUPERADMIN` privo di `has_maintenance_access` e verifica che possa creare un ticket via endpoint `/api/maintenance/tickets/`.

## Perché
In produzione i superadmin non riuscivano più a creare ticket dal tool manutenzioni perché mancava il loro ruolo nella whitelist dell'API. L'aggiornamento ripristina l'intento originale: i superadmin devono sempre poter operare, indipendentemente dai flag applicati ai profili operativi.

## Dove guardare nel codice
- **Permesso API**: `tickets/api.py`, classe `TicketPermission.has_permission` per l'accesso ai viewset.
- **Permessi calendario**: `tickets/api.py`, metodo `_calendar_permission_map`, che costruisce la mappa `permissionMap` esposta dal metadata endpoint.
- **Test di regressione**: `tickets/tests.py`, caso `test_superadmin_role_can_create_ticket_via_api_even_without_explicit_access_flag`.
