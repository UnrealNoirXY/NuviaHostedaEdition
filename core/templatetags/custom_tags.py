from django import template
from django.contrib.auth import get_user_model

from core.permissions import user_can as _user_can

register = template.Library()
User = get_user_model()


@register.filter(name='user_can')
def user_can(user, capability):
    """Espone il layer di permessi centralizzato ai template.

    Uso:  {% if request.user|user_can:'reviews' %} ... {% endif %}

    Così i template smettono di duplicare i controlli di ruolo
    (`{% if user.role == 'owner' or ... %}`) e usano la stessa fonte di verità
    di viste e navigazione.
    """
    try:
        return _user_can(user, capability)
    except KeyError:
        return False

@register.filter(name='get_avatar_url')
def get_avatar_url(user):
    """
    Returns the URL for a user's avatar.
    If the user has a custom avatar, it returns its URL.
    Otherwise, it returns a URL from ui-avatars.com.
    """
    if not user:
        return "https://ui-avatars.com/api/?name=?&background=random&color=fff&size=150"

    if hasattr(user, 'avatar') and user.avatar:
        return user.avatar.url

    # Fallback to ui-avatars
    if hasattr(user, 'username'):
        username = (user.username or "").strip()
        if username:
            name = username[0].upper()
            return f"https://ui-avatars.com/api/?name={name}&background=random&color=fff&size=150"

    # Default fallback if user object is weird
    return "https://ui-avatars.com/api/?name=?&background=random&color=fff&size=150"
