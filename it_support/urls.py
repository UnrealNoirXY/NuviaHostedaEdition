from django.urls import path
from . import views

app_name = 'it_support'

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
