# Nuvia — Design System (Fase 2)

Linguaggio visivo unico della suite. Obiettivo: **una sola identità** su tutte le
schermate (server-rendered Django + componenti React), eliminando il look divergente
per modulo.

## 1. Design tokens

Fonte di verità: **`static/css/design-tokens.css`**, caricato in `<head>` prima del CSS
Vite in tutti i base template (`base.html`, `base_landing.html`, `base_demo.html`).
Espone variabili CSS `--nv-*` per:

- **Colori**: brand, ink/testo, superfici, semantici (success/warning/danger/info).
- **Tipografia**: famiglia (`--nv-font-sans` = Poppins), scala `--nv-text-*`, pesi.
- **Spaziatura**: scala base-4 (`--nv-space-1` … `--nv-space-8`).
- **Raggi, ombre, transizioni**.
- **Z-index**: scala coerente (`--nv-z-sidebar`/`--nv-z-modal`/…) per sostituire i
  valori arbitrari sparsi nel codice (es. `z-index: 9000000000000` nella guida in-app).

**Regola d'oro:** nessun componente deve hardcodare colori/spaziature — usare i token.
Le variabili legacy (`--theme-color-main`, `--theme-color-secondary`) restano valide
come ponte di compatibilità, agganciate ai token: migrazione progressiva, zero rotture.

## 2. Tema chiaro/scuro

I token cambiano sotto `[data-theme="dark"]` (impostato su `<body>` da `user.theme`).
I componenti che usano i token ereditano il tema senza codice extra.

## 3. Navigazione = permessi

Le voci di menu (hub e sidebar) sono gate-ate dalla **stessa** fonte dei permessi:

- Hub: registro dichiarativo `core/navigation.py` filtrato da `core/permissions.user_can`.
- Sidebar (`partials/_sidebar.html`): voci a capability mappata 1:1 usano il filtro
  `{% if user|user_can:'<capability>' %}` invece dei ruoli cablati.

Così "ciò che vedo" e "ciò a cui accedo" non possono divergere.

## 4. Shell applicativa

Una sola shell (in `core/templates/core/base.html`):
`app-shell` → `app-shell__sidebar` + `app-shell__main` (`app-topbar`, `app-content`,
`app-footer`). Le pagine estendono `base.html` e riempiono `{% block content %}`.

## 5. Libreria componenti

Costruita **sui token**, condivisa tra Django e React:

- **CSS**: `frontend/src/styles/ui-components.css` (importato in `main.css`) — classi
  `.nv-btn`, `.nv-card`, `.nv-badge`, `.nv-table`, `.nv-alert`, `.nv-empty`, `.nv-spinner`.
  Usabili direttamente anche nei template Django.
- **React**: `frontend/src/components/ui/` — `Button`, `Card`, `Badge`, `EmptyState`,
  `Spinner`, con entry unico `index.js`:

  ```jsx
  import { Button, Card, EmptyState } from 'components/ui';
  ```

Regola: i nuovi schermi usano questi componenti invece di stili ad hoc.

## 6. Roadmap di adozione (incrementale)
1. ✅ Token centralizzati + caricati nei base template.
2. ✅ Sidebar agganciata al layer permessi.
3. ✅ Libreria componenti riusabile (CSS + React) sui token.
4. ⏳ Migrare i moduli esistenti (SCSS/React) a consumare token e componenti `ui/`.
5. ⏳ Deprecare `base_demo`/`base_landing` come varianti minime di `base.html`.
