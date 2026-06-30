"""Registro dichiarativo della navigazione dell'hub — Fase 1 del ridisegno.

Prima la lista degli strumenti dell'hub era costruita a mano in ``get_hub_tools``
con ~14 blocchi ``add_tool(condition=...)``: ogni condizione di accesso era
duplicata rispetto alle viste, con il rischio di mostrare uno strumento a chi poi
non poteva usarlo (o viceversa).

Ora ogni strumento dichiara la **capability** richiesta (vedi ``core.permissions``)
e l'hub si genera filtrando per ``user_can``. Aggiungere/spostare uno strumento =
aggiungere una riga a ``HUB_TOOLS``, senza logica di permessi duplicata.
"""

from __future__ import annotations

from dataclasses import dataclass

from django.urls import reverse

from .permissions import Capability, user_can


@dataclass(frozen=True)
class HubTool:
    capability: str
    label: str
    description: str
    icon: str
    icon_class: str
    url_name: str
    button_label: str
    button_class: str

    def as_context(self) -> dict:
        return {
            "label": self.label,
            "description": self.description,
            "icon": self.icon,
            "icon_class": self.icon_class,
            "url": reverse(self.url_name),
            "button_label": self.button_label,
            "button_class": self.button_class,
        }


# Ordine = ordine di visualizzazione nell'hub.
HUB_TOOLS: list[HubTool] = [
    HubTool(
        capability=Capability.MAINTENANCE,
        label="Gestione Manutenzioni",
        description="Crea e gestisci i ticket di manutenzione per i resort.",
        icon="fas fa-wrench",
        icon_class="text-primary",
        url_name="maintenance_tool_home",
        button_label="Apri Strumento",
        button_class="btn btn-primary",
    ),
    HubTool(
        capability=Capability.INVENTORY,
        label="Inventario",
        description="Visualizza le giacenze e i movimenti di magazzino per resort.",
        icon="fas fa-boxes-stacked",
        icon_class="text-success",
        url_name="inventory:list",
        button_label="Apri Strumento",
        button_class="btn btn-success",
    ),
    HubTool(
        capability=Capability.IT_SUPPORT,
        label="Supporto IT",
        description="Richiedi assistenza per problemi hardware, software o di rete.",
        icon="fas fa-headset",
        icon_class="text-danger",
        url_name="it_support:it_ticket_list",
        button_label="Apri Strumento",
        button_class="btn btn-danger",
    ),
    HubTool(
        capability=Capability.REVIEWS,
        label="Analisi Recensioni",
        description="Analizza le recensioni da Booking, TripAdvisor e altri portali.",
        icon="fas fa-star",
        icon_class="text-success",
        url_name="reviews:dashboard",
        button_label="Apri Strumento",
        button_class="btn btn-success",
    ),
    HubTool(
        capability=Capability.FINANCIALS,
        label="Controllo Amministrativo",
        description="Budget, consuntivi e insight finanziari integrati con ordini ed economato.",
        icon="fas fa-chart-line",
        icon_class="text-primary",
        url_name="financials:dashboard",
        button_label="Apri Strumento",
        button_class="btn btn-primary",
    ),
    HubTool(
        capability=Capability.DOCUMENTS_ADMIN,
        label="Amministrazione",
        description="Gestisci i documenti degli utenti, come buste paga e contratti.",
        icon="fas fa-file-invoice",
        icon_class="text-info",
        url_name="documents:document_list",
        button_label="Apri Strumento",
        button_class="btn btn-info",
    ),
    HubTool(
        capability=Capability.HR_BACHECA,
        label="Bacheca Nuvia",
        description="Consulta comunicazioni personali, documenti HR e buste paga.",
        icon="fas fa-clipboard-list",
        icon_class="text-primary",
        url_name="hr_portal:bacheca",
        button_label="Apri Bacheca",
        button_class="btn btn-primary",
    ),
    HubTool(
        capability=Capability.HR_PORTAL,
        label="Portale HR",
        description="Suite HR riservata per comunicazioni, batch e gestione buste paga.",
        icon="fas fa-id-badge",
        icon_class="text-primary",
        url_name="hr_portal:portal",
        button_label="Apri Portale",
        button_class="btn btn-primary",
    ),
    HubTool(
        capability=Capability.PURCHASE_ORDERS,
        label="Buoni d'Ordine",
        description="Crea e gestisci gli ordini di acquisto per fornitori e prodotti.",
        icon="fas fa-shopping-cart",
        icon_class="text-warning",
        url_name="purchase_orders:list",
        button_label="Apri Strumento",
        button_class="btn btn-warning",
    ),
    HubTool(
        capability=Capability.ECONOMATO,
        label="Economato Intelligente",
        description="Supervisiona richieste, stock e budget con workflow multi-resort e accessi granulari.",
        icon="fas fa-warehouse",
        icon_class="text-primary",
        url_name="economato:app",
        button_label="Apri App",
        button_class="btn btn-primary",
    ),
    HubTool(
        capability=Capability.NUVIA_MAIL,
        label="Nuvia Mail",
        description="Accedi in modo opzionale alla tua email aziendale con una guida IMAP/SMTP semplice e mobile-first.",
        icon="fas fa-envelope-open-text",
        icon_class="text-primary",
        url_name="core:nuvia_mail",
        button_label="Configura Mail",
        button_class="btn btn-primary",
    ),
    HubTool(
        capability=Capability.PROCEDURES,
        label="Procedure Operative",
        description="Consulta i manuali e le procedure standard per il tuo settore.",
        icon="fas fa-book-open",
        icon_class="text-procedures",
        url_name="procedures:procedure_list",
        button_label="Apri Strumento",
        button_class="btn btn-procedures",
    ),
    HubTool(
        capability=Capability.PROFILE_CARDS,
        label="Schede Profilo Wallet",
        description="Crea layout/template e condividi schede profilo pubbliche con wallet/vCard.",
        icon="fas fa-id-card",
        icon_class="text-primary",
        url_name="profile_cards:admin_dashboard",
        button_label="Apri Gestione",
        button_class="btn btn-primary",
    ),
]


def get_hub_tools(user) -> list[dict]:
    """Lista (pronta per il template) degli strumenti visibili a ``user``."""
    return [tool.as_context() for tool in HUB_TOOLS if user_can(user, tool.capability)]
