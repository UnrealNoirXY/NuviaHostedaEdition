from django.shortcuts import render

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
    """Strumenti visibili nell'hub per ``user``.

    La definizione degli strumenti e le regole di accesso vivono ora nel registro
    dichiarativo ``core.navigation`` (filtrato da ``core.permissions.user_can``),
    così navigazione e autorizzazione condividono un'unica fonte di verità.
    """
    from .navigation import get_hub_tools as _get_hub_tools

    return _get_hub_tools(user)
