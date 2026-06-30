from django.shortcuts import render
from django.urls import reverse

from accounts.models import User
from .models import PlatformSettings

def themed_render(request, template_name, context=None):
    """
    A custom render function that injects theme colors, platform settings,
    and navigation context into the template context.
    """
    if context is None:
        context = {}

    # Load platform settings from the database.
    # The .load() method on the model ensures the singleton object is created if it doesn't exist.
    try:
        settings = PlatformSettings.load()
        context['platform_name'] = settings.platform_name
        context.setdefault('theme_color', settings.primary_color)
        context.setdefault('theme_color_secondary', settings.secondary_color)
    except Exception:
        context.setdefault('platform_name', 'Noir Tools Kit')
        context.setdefault('theme_color', '#23395d')
        context.setdefault('theme_color_secondary', '#406fa6')

    # Determine tool context from the request's URL path to display the correct navigation.
    path = request.path
    nav_context = None
    if '/maintenance/' in path or '/ticket/' in path or '/management/' in path:
        nav_context = 'maintenance'
    elif '/reviews/' in path:
        nav_context = 'reviews'

    # Add the nav_context to the context dictionary if a tool context is found.
    # The base template will use this to show/hide the tool-specific navbar.
    if nav_context:
        context['nav_context'] = nav_context

    return render(request, template_name, context)


def get_hub_tools(user):
    tools = []
    hr_portal_access = (
        user.is_superuser
        or user.role
        in {
            User.SUPERADMIN,
            User.OWNER,
            User.RISORSE_UMANE,
        }
    )

    def add_tool(
        *,
        condition,
        label,
        description,
        icon,
        icon_class,
        url_name,
        button_label,
        button_class,
    ):
        if condition:
            tools.append(
                {
                    'label': label,
                    'description': description,
                    'icon': icon,
                    'icon_class': icon_class,
                    'url': reverse(url_name),
                    'button_label': button_label,
                    'button_class': button_class,
                }
            )

    add_tool(
        condition=user.is_superuser or getattr(user, 'has_maintenance_access', False),
        label='Gestione Manutenzioni',
        description='Crea e gestisci i ticket di manutenzione per i resort.',
        icon='fas fa-wrench',
        icon_class='text-primary',
        url_name='maintenance_tool_home',
        button_label='Apri Strumento',
        button_class='btn btn-primary',
    )

    add_tool(
        condition=getattr(user, 'has_inventory_access', False),
        label='Inventario',
        description='Visualizza le giacenze e i movimenti di magazzino per resort.',
        icon='fas fa-boxes-stacked',
        icon_class='text-success',
        url_name='inventory:list',
        button_label='Apri Strumento',
        button_class='btn btn-success',
    )

    add_tool(
        condition=True,
        label='Supporto IT',
        description='Richiedi assistenza per problemi hardware, software o di rete.',
        icon='fas fa-headset',
        icon_class='text-danger',
        url_name='it_support:it_ticket_list',
        button_label='Apri Strumento',
        button_class='btn btn-danger',
    )

    add_tool(
        condition=user.is_superuser or getattr(user, 'has_reviews_access', False),
        label='Analisi Recensioni',
        description='Analizza le recensioni da Booking, TripAdvisor e altri portali.',
        icon='fas fa-star',
        icon_class='text-success',
        url_name='reviews:dashboard',
        button_label='Apri Strumento',
        button_class='btn btn-success',
    )

    add_tool(
        condition=user.is_superuser
        or user.role
        in {
            User.SUPERADMIN,
            User.OWNER,
            User.DIRECTOR,
            User.ADMINISTRATIVE,
        },
        label='Controllo Amministrativo',
        description='Budget, consuntivi e insight finanziari integrati con ordini ed economato.',
        icon='fas fa-chart-line',
        icon_class='text-primary',
        url_name='financials:dashboard',
        button_label='Apri Strumento',
        button_class='btn btn-primary',
    )

    add_tool(
        condition=user.is_superuser
        or user.role
        in {
            User.ADMINISTRATIVE,
            User.RISORSE_UMANE,
        },
        label='Amministrazione',
        description='Gestisci i documenti degli utenti, come buste paga e contratti.',
        icon='fas fa-file-invoice',
        icon_class='text-info',
        url_name='documents:document_list',
        button_label='Apri Strumento',
        button_class='btn btn-info',
    )

    add_tool(
        condition=True,
        label='Bacheca Nuvia',
        description='Consulta comunicazioni personali, documenti HR e buste paga.',
        icon='fas fa-clipboard-list',
        icon_class='text-primary',
        url_name='hr_portal:bacheca',
        button_label='Apri Bacheca',
        button_class='btn btn-primary',
    )

    add_tool(
        condition=hr_portal_access,
        label='Portale HR',
        description='Suite HR riservata per comunicazioni, batch e gestione buste paga.',
        icon='fas fa-id-badge',
        icon_class='text-primary',
        url_name='hr_portal:portal',
        button_label='Apri Portale',
        button_class='btn btn-primary',
    )

    add_tool(
        condition=getattr(user, 'can_manage_purchase_orders', False),
        label="Buoni d'Ordine",
        description='Crea e gestisci gli ordini di acquisto per fornitori e prodotti.',
        icon='fas fa-shopping-cart',
        icon_class='text-warning',
        url_name='purchase_orders:list',
        button_label='Apri Strumento',
        button_class='btn btn-warning',
    )

    add_tool(
        condition=user.is_superuser
        or user.role
        in {
            User.OWNER,
            User.CAPO_ECONOMO,
            User.ECONOMO,
            User.DIRECTOR,
        },
        label='Economato Intelligente',
        description='Supervisiona richieste, stock e budget con workflow multi-resort e accessi granulari.',
        icon='fas fa-warehouse',
        icon_class='text-primary',
        url_name='economato:app',
        button_label='Apri App',
        button_class='btn btn-primary',
    )

    add_tool(
        condition=True,
        label='Nuvia Mail',
        description='Accedi in modo opzionale alla tua email aziendale con una guida IMAP/SMTP semplice e mobile-first.',
        icon='fas fa-envelope-open-text',
        icon_class='text-primary',
        url_name='core:nuvia_mail',
        button_label='Configura Mail',
        button_class='btn btn-primary',
    )

    add_tool(
        condition=True,
        label='Procedure Operative',
        description='Consulta i manuali e le procedure standard per il tuo settore.',
        icon='fas fa-book-open',
        icon_class='text-procedures',
        url_name='procedures:procedure_list',
        button_label='Apri Strumento',
        button_class='btn btn-procedures',
    )

    add_tool(
        condition=user.is_superuser or user.role in {User.SUPERADMIN},
        label='Schede Profilo Wallet',
        description='Crea layout/template e condividi schede profilo pubbliche con wallet/vCard.',
        icon='fas fa-id-card',
        icon_class='text-primary',
        url_name='profile_cards:admin_dashboard',
        button_label='Apri Gestione',
        button_class='btn btn-primary',
    )

    return tools
