from django.urls import path
from django.conf import settings
from core.views import decommissioned_module_view
from . import views

app_name = 'it_support'

if settings.ENABLE_INTERNAL_TICKETS:
    urlpatterns = [
        path('', views.it_ticket_list, name='it_ticket_list'),
        path('nuovo/', views.it_ticket_create, name='it_ticket_create'),
        path('gestione/', views.it_ticket_management_list, name='it_ticket_management_list'),
        path('chat-attive/', views.active_chats_list_view, name='active_chats_list'),
        path('report/', views.it_reporting_dashboard, name='it-reporting-dashboard'),

        # Ticket specific actions
        path('<int:pk>/', views.it_ticket_detail, name='it_ticket_detail'),
        path('<int:pk>/modifica/', views.it_ticket_update, name='it_ticket_update'),

        # Chat lifecycle
        path('<int:pk>/richiedi-chat/', views.request_chat, name='request_chat'),
        path('<int:pk>/accetta-chat/', views.accept_chat, name='accept_chat'),
        path('<int:pk>/rifiuta-chat/', views.decline_chat, name='decline_chat'),
        path('<int:pk>/termina-chat/', views.end_chat, name='end_chat'),

        # API-like endpoints for chat
        path('api/chat/<int:pk>/messages/', views.chat_messages, name='chat_messages'),
        path('api/chat/<int:pk>/messages/create/', views.chat_message_create, name='chat_messages_create'),
    ]
else:
    urlpatterns = [
        path('', decommissioned_module_view, {'module': 'tickets'}, name='it_ticket_list'),
        path('nuovo/', decommissioned_module_view, {'module': 'tickets'}, name='it_ticket_create'),
        path('gestione/', decommissioned_module_view, {'module': 'tickets'}, name='it_ticket_management_list'),
        path('chat-attive/', decommissioned_module_view, {'module': 'tickets'}, name='active_chats_list'),
        path('report/', decommissioned_module_view, {'module': 'tickets'}, name='it-reporting-dashboard'),
        path('<int:pk>/', decommissioned_module_view, {'module': 'tickets'}, name='it_ticket_detail'),
        path('<int:pk>/modifica/', decommissioned_module_view, {'module': 'tickets'}, name='it_ticket_update'),
        path('<int:pk>/richiedi-chat/', decommissioned_module_view, {'module': 'tickets'}, name='request_chat'),
        path('<int:pk>/accetta-chat/', decommissioned_module_view, {'module': 'tickets'}, name='accept_chat'),
        path('<int:pk>/rifiuta-chat/', decommissioned_module_view, {'module': 'tickets'}, name='decline_chat'),
        path('<int:pk>/termina-chat/', decommissioned_module_view, {'module': 'tickets'}, name='end_chat'),
        path('api/chat/<int:pk>/messages/', decommissioned_module_view, {'module': 'tickets'}, name='chat_messages'),
        path('api/chat/<int:pk>/messages/create/', decommissioned_module_view, {'module': 'tickets'}, name='chat_messages_create'),
    ]
