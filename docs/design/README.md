# Nuvia OS — Nuovo design system "Mission Control"

Studio per il ridisegno completo del frontend (Fase 2/3 del piano).
Direzione approvata: **control center scuro raffinato**, dark di default, accent **ambra/oro**,
navigazione a **rail di icone + command palette (⌘K)**.

## Prototipo navigabile

`docs/design/prototype/` — HTML autonomi (nessun CDN), apribili direttamente nel browser:

| File | Schermata |
|---|---|
| `login.html` | Accesso (split brand + form) |
| `hub.html` | Hub operativo per-ruolo (alert + strumenti con stato live) |
| `reviews.html` | Dashboard Recensioni (KPI+sparkline, donut, tabella densa) |
| `hr.html` | Portale HR (coda buste paga, comunicazioni, stato batch) |
| `tokens.css` | **Design tokens condivisi** (fonte di verità unica) |

## Principi

- **Colore:** un solo sfondo antracite profondo (`#0A0D14`, no gradienti) + superfici a gradini;
  bordi hairline 1px; **un solo accent** (ambra `#F5B544`) usato con parsimonia; semantici
  verde/giallo/rosso per gli stati.
- **Tipografia:** sans di sistema per il testo, **monospace per i numeri** (look "strumento di precisione").
- **Densità alta:** molta informazione per schermata, pensata per lavoro operativo veloce.
- **Componenti unici:** `panel`, `kpi`, `tag`, `chip`, `btn`, `table`, rail, topbar — sostituiscono
  gli 8+ sistemi di card e i 3 sistemi di token attuali (`ntk`/`nv`/Bootstrap).
- **Accessibilità:** contrasto AA, focus visibili, target ≥ 40px (da rifinire in implementazione).

## Prossimi passi

1. ✅ Direzione visiva approvata + prototipo multi-schermata.
2. ⏳ Formalizzare i token definitivi e la libreria componenti (CSS unico + componenti React).
3. ⏳ Implementazione progressiva nell'app reale: shell (rail+topbar+⌘K) → login → hub →
   moduli prioritari (Recensioni, HR) → resto, con verifica a video schermata per schermata.
4. ⏳ Dismissione graduale dei vecchi token/CSS (`--ntk-*`, 36 file SCSS) man mano.
