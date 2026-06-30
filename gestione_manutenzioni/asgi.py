import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import it_support.routing

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestione_manutenzioni.settings')

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            it_support.routing.websocket_urlpatterns
        )
    ),
})
