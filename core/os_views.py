"""Anteprima del nuovo frontend 'Nuvia OS · Control Center'.

Prima slice di implementazione della nuova direzione grafica: l'Hub reale,
cablato ai dati/permessi veri (registro navigazione + core.permissions.user_can),
servito su una route di anteprima dedicata così non tocca l'app esistente.
"""

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .navigation import HUB_TOOLS
from .permissions import user_can

# Icona (emoji) per capability: rende ovunque, indipendente da Font Awesome/CDN.
CAPABILITY_EMOJI = {
    "maintenance": "🔧",
    "inventory": "📦",
    "it_support": "🎧",
    "reviews": "⭐",
    "financials": "📈",
    "documents_admin": "🗂️",
    "hr_bacheca": "📋",
    "hr_portal": "🪪",
    "purchase_orders": "🛒",
    "economato": "🏬",
    "nuvia_mail": "✉️",
    "procedures": "📖",
    "profile_cards": "🎴",
}


@login_required
def os_hub_preview(request):
    user = request.user
    tools = []
    for tool in HUB_TOOLS:
        if user_can(user, tool.capability):
            ctx = tool.as_context()
            ctx["emoji"] = CAPABILITY_EMOJI.get(tool.capability, "▪️")
            tools.append(ctx)

    context = {
        "tools": tools,
        "os_preview": True,
    }
    return render(request, "core/os_hub.html", context)
