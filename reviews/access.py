"""Accesso e visibilità delle recensioni — fonte di verità unica (Fase 3).

Prima il gate (`allowed_roles = [...]`) e lo scoping per company/resort erano
copia-incollati in ~5 viste: rischio concreto che un punto venisse aggiornato e gli
altri no. Qui vivono una sola volta e sono allineati al layer permessi centralizzato
(`core.permissions`), così la navigazione (hub/sidebar) e l'autorizzazione delle viste
non possono divergere.

Modello:
  - chi può accedere   -> `can_access_reviews(user)` == `user_can(user, REVIEWS)`
  - cosa può vedere    -> `scope_reviews(queryset, user)` (scoping per company/resort)
"""

from accounts.models import User
from core.permissions import Capability, user_can

# Ruoli che vedono TUTTE le recensioni della propria società.
REVIEW_COMPANY_ROLES = frozenset(
    {
        User.OWNER,
        User.CORPORATE,
        User.RISORSE_UMANE,
        User.CAPO_ECONOMO,
        User.HEAD_MAINTAINER,
    }
)


def can_access_reviews(user) -> bool:
    """True se l'utente può accedere alla sezione recensioni.

    Allineato 1:1 alla capability REVIEWS: superuser, ruoli abilitati o flag
    has_reviews_access. È la stessa regola che decide la visibilità nell'hub.
    """
    return user_can(user, Capability.REVIEWS)


def scope_reviews(queryset, user):
    """Limita ``queryset`` alle recensioni che ``user`` può vedere.

    - superuser: tutte
    - ruoli azienda: recensioni della propria società
    - direttore: recensioni del proprio resort
    - altrimenti: nessuna (mai un fallback "tutte", per evitare leak cross-azienda)
    """
    if getattr(user, "is_superuser", False):
        return queryset

    role = getattr(user, "role", None)

    if role in REVIEW_COMPANY_ROLES:
        return queryset.filter(resort__company=user.company) if user.company else queryset.none()

    if role == User.DIRECTOR:
        return queryset.filter(resort=user.resort) if user.resort else queryset.none()

    return queryset.none()
