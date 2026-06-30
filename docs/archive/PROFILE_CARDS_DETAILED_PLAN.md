# Piano Dettagliato — Nuovo Strumento "Schede Profilo Wallet"

## 1) Obiettivo e vincoli

Realizzare un nuovo strumento monolitico, isolato dagli altri tool, che permetta di:

- creare e gestire schede profilo condivisibili (cliente/collega),
- aggiungere schede ad Apple Wallet (iOS, `.pkpass`) e Google Wallet (Android),
- rendere la scheda **visionabile anche senza accesso** tramite link pubblico firmato,
- inviare la scheda via mail con la **stessa configurazione SMTP usata per OTP** (non SMTP HR),
- includere nella scheda un pulsante **"Invia Contatto"** per condividere rapidamente il profilo,
- consentire al **solo superamministratore** la configurazione grafica sia del pass wallet sia del profilo web pubblico.

---

## 2) Scope funzionale

### 2.1 Ruoli e permessi

- **Superamministratore**:
  - crea template grafici,
  - crea/aggiorna/disattiva schede,
  - decide visibilità e durata link pubblico,
  - invia singolarmente o in batch via mail,
  - monitora log invii/aperture/aggiunte wallet.
- **Utenti non autenticati (pubblico)**:
  - possono aprire il link pubblico tokenizzato,
  - vedere il profilo pubblico,
  - usare pulsante "Invia Contatto",
  - aggiungere al wallet,
  - scaricare vCard.

> Nessuna modifica ai permessi degli altri strumenti: nuovo namespace, nuove API, nuove tabelle.

### 2.2 Dati scheda (MVP + estensioni)

Campi base richiesti:

- logo società (upload),
- nome,
- cognome,
- ruolo,
- email,
- QR code (link pubblico scheda).

Campi consigliati:

- telefono,
- reparto,
- sede,
- note brevi,
- URL aziendale/LinkedIn,
- stato scheda: `draft`, `published`, `revoked`.

---

## 3) Requisito email: usare SMTP OTP (non HR)

## Regola architetturale

La spedizione schede deve usare il backend/credenziali mail del flusso OTP:

- utilizzare configurazione `EMAIL_*` + `DEFAULT_FROM_EMAIL`,
- non usare `HR_EMAIL_*` / `HR_FROM_EMAIL`.

### Implicazioni implementative

- creare servizio dedicato `send_profile_card_email(...)` che:
  - usa `get_connection(...)` con parametri OTP/default,
  - supporta allegati (`.pkpass`, `.vcf`, eventuale PDF anteprima),
  - template HTML/TXT dedicati,
  - retry e gestione errori coerenti con standard piattaforma.
- endpoint di test invio separato (analogo test SMTP già esistente), ma collegato al canale OTP.

---

## 4) Pulsante "Invia Contatto" nella scheda pubblica

## UX attesa

Nella pagina profilo pubblico, bottone principale: **"Invia Contatto"**.

Comportamento multi-canale:

1. **Mobile con Web Share API**: apre share sheet nativa con titolo/testo/link.
2. **Fallback desktop**:
   - copia link negli appunti,
   - apre `mailto:` precompilato,
   - opzionale apertura WhatsApp Web con testo precompilato.

Contenuto condiviso consigliato:

- Nome Cognome + ruolo,
- URL pubblico tokenizzato,
- call-to-action: "Aggiungi il mio contatto al wallet o scarica la vCard".

---

## 5) Configurazione grafica superadmin (wallet + profilo pubblico)

## 5.1 Builder grafico Template

Il superadmin deve poter configurare da UI:

- logo,
- colori primario/secondario,
- font e contrasto,
- immagini header/sfondo,
- ordine campi visualizzati,
- stile QR (dimensione, margine, etichetta),
- etichette custom (es. "Ruolo", "Contatto", "Invia Contatto").

## 5.2 Due viste separate ma coerenti

1. **Template Wallet Pass**
   - mapping campi per Apple/Google,
   - preview pass front/back,
   - validazione compatibilità (colori, risoluzioni, limiti stringhe).
2. **Template Profilo Pubblico**
   - preview responsive desktop/mobile,
   - pulsanti rapidi: Invia Contatto, Salva in rubrica, Add to Wallet.

## 5.3 Versioning template

- ogni modifica crea nuova versione,
- le schede già inviate possono:
  - restare congelate alla versione usata, oppure
  - aggiornarsi automaticamente (configurabile).

---

## 6) Proposta modello dati (nuova app dedicata)

App suggerita: `profile_cards`.

Tabelle principali:

1. `CardTemplate`
   - nome template, brand assets, JSON configurazione grafica, versione.
2. `ProfileCard`
   - anagrafica, stato, template associato, metadati generazione.
3. `ProfileCardPublicToken`
   - token firmato/hash, scadenza, revoca, contatori aperture.
4. `ProfileCardAsset`
   - file generati (`pkpass`, `vcf`, preview), checksum, timestamp.
5. `ProfileCardDelivery`
   - storico invii mail (destinatario, provider, stato, errore, tentativi).
6. `ProfileCardEvent`
   - audit eventi (create/update/send/open/share/add_wallet).

---

## 7) Architettura endpoint/UI

## 7.1 Endpoint interni (superadmin)

- CRUD template,
- CRUD schede,
- azione `publish/revoke`,
- azione `send_email` (singola/batch),
- endpoint anteprima grafica,
- endpoint rigenerazione asset wallet.

## 7.2 Endpoint pubblici (no login)

- `GET /cards/public/<token>/` profilo pubblico,
- `GET /cards/public/<token>/vcard` download vCard,
- `GET /cards/public/<token>/apple-pass` download `.pkpass`,
- `GET /cards/public/<token>/google-wallet` redirect/add flow,
- endpoint tracking eventi (open/share/add).

---

## 8) Sicurezza, privacy, conformità

- token pubblici firmati con scadenza (`max_age`) e revoca immediata,
- rate limiting endpoint pubblici,
- logging IP/user-agent solo se conforme policy privacy,
- possibilità di disattivare indicizzazione (`noindex`) sulle pagine pubbliche,
- minimizzazione dati: niente campi sensibili non necessari,
- audit completo per attività superadmin.

---

## 9) Strategia Wallet

## 9.1 Apple Wallet

- generazione `.pkpass` firmato (certificati Apple),
- gestione aggiornamento pass quando cambia scheda,
- fallback download vCard se pass non installabile.

## 9.2 Google Wallet

- creazione class/object tramite API Google Wallet,
- deep link "Add to Google Wallet",
- fallback pagina pubblica + vCard.

## 9.3 Fallback universale obbligatorio

Anche senza wallet:

- pagina profilo pubblica,
- vCard,
- bottone "Invia Contatto".

---

## 10) Piano di rilascio in fasi

## Fase 0 — Analisi tecnica e UX (3-5 giorni)

- allineamento campi,
- bozza design template,
- decisione su policy revoca/scadenza,
- definizione eventi e KPI.

## Fase 1 — MVP operativo (1 sprint)

- nuova app `profile_cards` con CRUD superadmin,
- profilo pubblico tokenizzato,
- QR code,
- vCard,
- pulsante "Invia Contatto",
- invio mail su SMTP OTP.

## Fase 2 — Template Builder avanzato (1 sprint)

- editor grafico completo,
- preview live wallet/web,
- versioning template,
- validazioni automatiche asset.

## Fase 3 — Apple Wallet (1 sprint)

- generazione e firma pass,
- download/attach email,
- monitoraggio installazioni.

## Fase 4 — Google Wallet (1 sprint)

- integrazione API,
- add flow Android,
- aggiornamento oggetti e revoca.

## Fase 5 — Hardening & KPI (1 sprint)

- dashboard metriche (aperture, share, add-wallet, bounce email),
- performance test endpoint pubblici,
- security review finale.

---

## 11) KPI consigliati

- tasso apertura link pubblico,
- tasso click "Invia Contatto",
- tasso download vCard,
- tasso Add to Apple Wallet,
- tasso Add to Google Wallet,
- tasso successo invio email (canale OTP),
- tempo medio creazione scheda.

---

## 12) Criteri di accettazione (DoD)

1. Solo superadmin può creare/modificare/revocare schede.
2. Email schede inviate via configurazione OTP/default SMTP.
3. Profilo pubblico accessibile senza login via token valido.
4. Pulsante "Invia Contatto" attivo con fallback cross-device.
5. Superadmin configura graficamente sia wallet pass sia pagina profilo.
6. Nessuna regressione sugli strumenti esistenti (routing/permessi/test).
7. Logging completo e revoca token immediata.

---

## 13) Rischi e mitigazioni

- **Certificati Apple Wallet complessi** → checklist operativa e ambiente staging dedicato.
- **Dipendenze API Google Wallet** → fallback universale sempre disponibile.
- **Abuso link pubblici** → rate limit + token scadenza breve + revoca one-click.
- **Scope creep grafico** → MVP con componenti bloccati, editor avanzato in fase successiva.

---

## 14) Decisioni chiave da confermare prima dello sviluppo

1. durata standard link pubblico (es. 30/90 giorni o senza scadenza con revoca manuale),
2. campi obbligatori oltre a nome/cognome/ruolo/email,
3. livello personalizzazione grafica iniziale del builder,
4. comportamento aggiornamento pass già installati,
5. eventuale brand multi-società con template separati.
