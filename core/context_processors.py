from django.conf import settings
from django.core.cache import cache
from django.db.models import Q

from accounts.models import User
from it_support.models import IT_Ticket

def active_chats_processor(request):
    base_context = {
        'web_push_public_key': getattr(settings, 'WEB_PUSH_VAPID_PUBLIC_KEY', ''),
    }

    if not request.user.is_authenticated:
        return base_context

    cache_key = f'active_chats_user_{request.user.id}'
    cached_data = cache.get(cache_key)

    if cached_data is not None:
        cached_data.update(base_context)
        return cached_data

    is_privileged = request.user.is_superuser or \
                    (hasattr(request.user, 'role') and request.user.role == User.IT_TECHNICIAN)

    active_chats_query = Q(chat_status='active')

    if not is_privileged:
        involvement_query = Q(user=request.user) | Q(assigned_to=request.user)
        active_chats_query &= involvement_query

    # The query is executed here
    active_chats = IT_Ticket.objects.filter(active_chats_query).order_by('-updated_at')

    data_to_cache = {
        'active_chats_list': active_chats,
        'has_active_chats': active_chats.exists(),
        'is_it_staff': is_privileged,
    }

    # Cache the result for 15 seconds
    cache.set(cache_key, data_to_cache, 15)
    data_to_cache.update(base_context)
    return data_to_cache
