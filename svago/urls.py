from django.urls import path
from . import views

app_name = 'svago'

urlpatterns = [
    path('', views.lobby_view, name='lobby'),
    path('setup/', views.setup_gamertag_view, name='setup_gamertag'),
    path('invite/<int:player_id>/', views.invite_player_view, name='invite_player'),
    path('accept/<int:game_id>/', views.accept_invitation_view, name='accept_invitation'),
    path('decline/<int:game_id>/', views.decline_invitation_view, name='decline_invitation'),
    path('cancel/<int:game_id>/', views.cancel_invitation_view, name='cancel_invitation'),
    path('game/<int:game_id>/', views.game_view, name='game_view'),
    path('game/<int:game_id>/state/', views.game_state_view, name='game_state'),
    path('game/<int:game_id>/move/', views.make_move_view, name='make_move'),
    path('tris/', views.tris_view, name='tris'), # Single player
    path('noir-invaders/', views.noir_invaders_view, name='noir_invaders'),
    path('snake-noir/', views.snake_noir_view, name='snake_noir'),
    path('noir-tris/', views.noir_tris_view, name='noir_tris'),
    path('noir-man/', views.noir_man_view, name='noir_man'),
    # HTMX partial update URLs
    path('game-status/', views.game_status_view, name='game_status'),
    path('online-users/', views.online_users_view, name='online_users'),
]
