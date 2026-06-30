# HR Portal Entry Points (Last Update)

This note documents the entry points added for the HR portal so reviewers can quickly understand the integration.

## What was added
- A dedicated React mount template (`hr_portal/templates/hr_portal/react_root.html`) exposed via `hr_portal/urls.py` and served by `HRPortalView`.
- Hub and sidebar links that surface the portal only to authorized users (superusers or the HR role) via updates in `core/templates/core/hub.html` and `core/templates/partials/_sidebar.html`.
- Inclusion of the HR portal URL namespace in `gestione_manutenzioni/urls.py` so the route `/hr/` is reachable.
- The mobile shell navigation context now carries the HR link for eligible users through `core/api_views.py`.

## How access control works
- The template is protected by `LoginRequiredMixin` and checks `request.user.role == user.RISORSE_UMANE` or superuser privileges before rendering.
- The hub card, sidebar item, and mobile navigation link are conditioned on the same privilege check to avoid exposing the HR portal to unauthorized accounts.
