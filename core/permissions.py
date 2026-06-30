"""Layer di permessi centralizzato — Fase 1 del ridisegno.

Fonte di verità **unica** per "chi può accedere a cosa". Sostituisce i controlli
sparsi nel codice (``is_superuser``, ``role in {...}`` cablati, flag ``has_X_access``)
con una sola API dichiarativa:

    from core.permissions import Capability, user_can, capability_required

    if user_can(request.user, Capability.REVIEWS):
        ...

    @capability_required(Capability.FINANCIALS)
    def my_view(request):
        ...

La navigazione dell'hub (``core.navigation``) è generata dalle **stesse** regole,
così "ciò che vedo nell'hub" e "ciò a cui posso davvero accedere" non possono più
divergere — che era una delle cause dei bug di autorizzazione.

Regole di valutazione (in ordine):
    1. utente non autenticato            -> False
    2. capability marcata ``public``     -> True
    3. ``user.is_superuser``             -> True  (il superadmin vede/accede a tutto)
    4. ruolo dell'utente in ``roles``    -> True
    5. uno dei ``flags`` è True          -> True
    6. altrimenti                        -> False
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import wraps
from typing import Callable

from django.core.exceptions import PermissionDenied

from accounts.models import User


class Capability:
    """Capacità funzionali del prodotto (stringhe stabili, usabili nei template)."""

    MAINTENANCE = "maintenance"
    INVENTORY = "inventory"
    IT_SUPPORT = "it_support"
    REVIEWS = "reviews"
    FINANCIALS = "financials"
    DOCUMENTS_ADMIN = "documents_admin"
    HR_BACHECA = "hr_bacheca"
    HR_PORTAL = "hr_portal"
    PURCHASE_ORDERS = "purchase_orders"
    ECONOMATO = "economato"
    NUVIA_MAIL = "nuvia_mail"
    PROCEDURES = "procedures"
    PROFILE_CARDS = "profile_cards"


@dataclass(frozen=True)
class Rule:
    """Regola di accesso per una capability.

    ``roles``  : ruoli che concedono l'accesso.
    ``flags``  : nomi di attributi booleani su ``User`` che concedono l'accesso.
    ``public`` : se True, ogni utente autenticato ha accesso.
    """

    roles: frozenset = field(default_factory=frozenset)
    flags: tuple = ()
    public: bool = False


# Mappa dichiarativa capability -> regola. Replica fedelmente le condizioni che
# erano cablate in ``get_hub_tools`` e nelle viste, ma in un unico punto.
CAPABILITY_RULES: dict[str, Rule] = {
    Capability.MAINTENANCE: Rule(flags=("has_maintenance_access",)),
    Capability.INVENTORY: Rule(flags=("has_inventory_access",)),
    Capability.IT_SUPPORT: Rule(public=True),
    Capability.REVIEWS: Rule(flags=("has_reviews_access",)),
    Capability.FINANCIALS: Rule(
        roles=frozenset({User.SUPERADMIN, User.OWNER, User.DIRECTOR, User.ADMINISTRATIVE})
    ),
    Capability.DOCUMENTS_ADMIN: Rule(
        roles=frozenset({User.ADMINISTRATIVE, User.RISORSE_UMANE})
    ),
    Capability.HR_BACHECA: Rule(public=True),
    Capability.HR_PORTAL: Rule(
        roles=frozenset({User.SUPERADMIN, User.OWNER, User.RISORSE_UMANE})
    ),
    Capability.PURCHASE_ORDERS: Rule(flags=("can_manage_purchase_orders",)),
    Capability.ECONOMATO: Rule(
        roles=frozenset({User.OWNER, User.CAPO_ECONOMO, User.ECONOMO, User.DIRECTOR})
    ),
    Capability.NUVIA_MAIL: Rule(public=True),
    Capability.PROCEDURES: Rule(public=True),
    Capability.PROFILE_CARDS: Rule(roles=frozenset({User.SUPERADMIN})),
}


def user_can(user, capability: str) -> bool:
    """True se ``user`` ha la ``capability`` richiesta.

    Solleva ``KeyError`` se la capability non è registrata: è un errore di
    programmazione (typo) e va intercettato subito, non silenziato.
    """
    rule = CAPABILITY_RULES[capability]

    if user is None or not getattr(user, "is_authenticated", False):
        return False
    if rule.public:
        return True
    if getattr(user, "is_superuser", False):
        return True
    if getattr(user, "role", None) in rule.roles:
        return True
    return any(getattr(user, flag, False) for flag in rule.flags)


def capability_required(capability: str) -> Callable:
    """Decorator per function-based view: nega l'accesso (403) se manca la capability."""

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not user_can(request.user, capability):
                raise PermissionDenied
            return view_func(request, *args, **kwargs)

        return _wrapped

    return decorator


class CapabilityRequiredMixin:
    """Mixin per class-based view. Imposta ``required_capability`` sulla classe."""

    required_capability: str | None = None

    def dispatch(self, request, *args, **kwargs):
        if self.required_capability is None:
            raise ValueError("required_capability non impostata sulla view.")
        if not user_can(request.user, self.required_capability):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)
