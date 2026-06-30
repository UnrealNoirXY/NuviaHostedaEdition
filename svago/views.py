from django.shortcuts import render, redirect, get_object_or_404
import json
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from django.db import models
from accounts.models import User
from .models import GameSession
from notifications.models import Notification
from core.utils import themed_render
from .forms import GamerTagForm


@login_required
def setup_gamertag_view(request):
    if request.user.gamertag:
        return redirect('svago:lobby')

    if request.method == 'POST':
        form = GamerTagForm(request.POST)
        if form.is_valid():
            gamertag = form.cleaned_data['gamertag']
            request.user.gamertag = gamertag
            request.user.save(update_fields=['gamertag'])
            messages.success(request, f"GamerTag '{gamertag}' creato con successo! Benvenuto.")
            return redirect('svago:lobby')
    else:
        form = GamerTagForm()

    return themed_render(request, 'svago/setup_gamertag.html', {'form': form})


def check_winner(board):
    winning_combinations = [
        [0, 1, 2], [3, 4, 5], [6, 7, 8],  # Rows
        [0, 3, 6], [1, 4, 7], [2, 5, 8],  # Columns
        [0, 4, 8], [2, 4, 6]             # Diagonals
    ]
    for combo in winning_combinations:
        if board[combo[0]] and board[combo[0]] == board[combo[1]] == board[combo[2]]:
            return board[combo[0]]
    if all(cell for cell in board):
        return 'draw'
    return None

from django.utils import timezone
from django.db.models import Case, When, Value, BooleanField, Q

@login_required
def online_users_view(request):
    """
    Returns the HTML fragment containing the list of online users.
    """
    five_minutes_ago = timezone.now() - timezone.timedelta(minutes=5)
    users = User.objects.exclude(pk=request.user.pk).annotate(
        is_online=Case(
            When(last_seen__gte=five_minutes_ago, then=Value(True)),
            default=Value(False),
            output_field=BooleanField()
        )
    ).filter(is_online=True).order_by('username')
    context = {'users': users}
    return themed_render(request, 'svago/partials/_online_users.html', context)


@login_required
def game_status_view(request):
    """
    Returns the HTML fragment containing the game invitation and active game status.
    """
    pending_invitations = GameSession.objects.filter(player1=request.user, status=GameSession.STATUS_PENDING)
    game_invitations = GameSession.objects.filter(player2=request.user, status=GameSession.STATUS_PENDING)
    active_games = GameSession.objects.filter(
        Q(player1=request.user) | Q(player2=request.user),
        status=GameSession.STATUS_ACTIVE
    )
    context = {
        'pending_invitations': pending_invitations,
        'game_invitations': game_invitations,
        'active_games': active_games,
    }
    return themed_render(request, 'svago/partials/_lobby_status.html', context)


@login_required
def lobby_view(request):
    five_minutes_ago = timezone.now() - timezone.timedelta(minutes=5)

    users = User.objects.exclude(pk=request.user.pk).annotate(
        is_online=Case(
            When(last_seen__gte=five_minutes_ago, then=Value(True)),
            default=Value(False),
            output_field=BooleanField()
        )
    ).filter(is_online=True).order_by('username')

    pending_invitations = GameSession.objects.filter(player1=request.user, status=GameSession.STATUS_PENDING)
    game_invitations = GameSession.objects.filter(player2=request.user, status=GameSession.STATUS_PENDING)
    active_games = GameSession.objects.filter(
        Q(player1=request.user) | Q(player2=request.user),
        status=GameSession.STATUS_ACTIVE
    )

    # Fetch last 10 game-related notifications for the current user
    game_notifications = Notification.objects.filter(
        user=request.user,
        link__startswith='/svago/'
    ).order_by('-created_at')[:10]

    context = {
        'users': users,
        'pending_invitations': pending_invitations,
        'game_invitations': game_invitations,
        'active_games': active_games,
        'game_notifications': game_notifications,
    }
    return themed_render(request, 'svago/lobby.html', context)

@login_required
def invite_player_view(request, player_id):
    if request.method == 'POST':
        player2 = get_object_or_404(User, pk=player_id)
        player1 = request.user

        if player1 == player2:
            messages.error(request, "Non puoi invitare te stesso.")
            return redirect('svago:lobby')

        existing_game = GameSession.objects.filter(
            (models.Q(player1=player1, player2=player2) | models.Q(player1=player2, player2=player1)),
            status__in=[GameSession.STATUS_PENDING, GameSession.STATUS_ACTIVE]
        ).first()

        if existing_game:
            messages.warning(request, f"Hai già una partita in corso o in sospeso con {player2.username}.")
            return redirect('svago:lobby')

        game = GameSession.objects.create(player1=player1, player2=player2, current_turn=player1)

        invitation_url = request.build_absolute_uri(reverse('svago:lobby'))
        Notification.objects.create(
            user=player2,
            title="Nuovo invito di gioco",
            message=f"Hai ricevuto un invito a giocare a Tris da {player1.username}!",
            link=invitation_url,
            category=Notification.Category.GENERAL,
            priority=Notification.Priority.NORMAL,
            icon='fa-gamepad',
            delivery_channels=['in_app', 'push'],
            source='svago',
            metadata={'game': 'tris', 'event': 'invite'},
        )

        messages.success(request, f"Invito inviato a {player2.username}!")
    return redirect('svago:lobby')

@login_required
def accept_invitation_view(request, game_id):
    game = get_object_or_404(GameSession, pk=game_id, player2=request.user, status=GameSession.STATUS_PENDING)
    if request.method == 'POST':
        game.status = GameSession.STATUS_ACTIVE
        game.save()

        game_url = reverse('svago:game_view', args=[game.id])
        Notification.objects.create(
            user=game.player1,
            title="Invito accettato",
            message=f"{request.user.username} ha accettato il tuo invito! La partita è iniziata.",
            link=game_url,
            category=Notification.Category.GENERAL,
            priority=Notification.Priority.NORMAL,
            icon='fa-handshake',
            delivery_channels=['in_app', 'push'],
            source='svago',
            metadata={'game': 'tris', 'event': 'accepted', 'game_id': game.id},
        )
        return redirect(game_url)
    return redirect('svago:lobby')

@login_required
def decline_invitation_view(request, game_id):
    game = get_object_or_404(GameSession, pk=game_id, player2=request.user, status=GameSession.STATUS_PENDING)
    if request.method == 'POST':
        lobby_url = reverse('svago:lobby')
        Notification.objects.create(
            user=game.player1,
            title="Invito rifiutato",
            message=f"{request.user.username} ha rifiutato il tuo invito a giocare.",
            link=lobby_url,
            category=Notification.Category.ALERT,
            priority=Notification.Priority.LOW,
            icon='fa-circle-xmark',
            delivery_channels=['in_app'],
            source='svago',
            metadata={'game': 'tris', 'event': 'declined', 'game_id': game.id},
        )
        game.delete()
        messages.info(request, "Hai rifiutato l'invito.")
    return redirect('svago:lobby')

@login_required
def cancel_invitation_view(request, game_id):
    game = get_object_or_404(GameSession, pk=game_id, player1=request.user, status=GameSession.STATUS_PENDING)
    if request.method == 'POST':
        game.delete()
        messages.info(request, "Hai annullato l'invito.")
    return redirect('svago:lobby')

@login_required
def game_view(request, game_id):
    game = get_object_or_404(GameSession, pk=game_id)
    if not (request.user == game.player1 or request.user == game.player2):
        messages.error(request, "Non sei autorizzato a vedere questa partita.")
        return redirect('svago:lobby')

    context = {
        'game': game,
    }
    return themed_render(request, 'svago/game_room.html', context)

@login_required
def tris_view(request):
    """ This view is now for the single player version. """
    return themed_render(request, 'svago/tris.html')

@login_required
def noir_invaders_view(request):
    """ Renders the Noir Invaders game page. """
    return themed_render(request, 'svago/noir_invaders.html')

@login_required
def snake_noir_view(request):
    """ Renders the Snake Noir game page. """
    return themed_render(request, 'svago/snake_noir.html')

@login_required
def noir_tris_view(request):
    """ Renders the NoirTris game page. """
    return themed_render(request, 'svago/noir_tris.html')

@login_required
def noir_man_view(request):
    """ Renders the Noir-Man game page. """
    return themed_render(request, 'svago/noir_man.html')


@login_required
def game_state_view(request, game_id):
    game = get_object_or_404(GameSession, pk=game_id)
    if not (request.user == game.player1 or request.user == game.player2):
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    winner_username = None
    if game.winner:
        winner_username = game.winner.username

    return JsonResponse({
        'board_state': game.get_board_state(),
        'current_turn_id': game.current_turn.id if game.current_turn else None,
        'current_turn_username': game.current_turn.username if game.current_turn else None,
        'player1_id': game.player1.id,
        'player2_id': game.player2.id,
        'status': game.status,
        'winner_id': game.winner.id if game.winner else None,
        'winner_username': winner_username,
    })


@login_required
def make_move_view(request, game_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method is allowed'}, status=405)

    game = get_object_or_404(GameSession, pk=game_id)

    # Validation
    if not (request.user == game.player1 or request.user == game.player2):
        return JsonResponse({'error': 'You are not a player in this game.'}, status=403)
    if game.status != GameSession.STATUS_ACTIVE:
        return JsonResponse({'error': 'This game is not active.'}, status=400)
    if request.user != game.current_turn:
        return JsonResponse({'error': 'It is not your turn.'}, status=400)

    try:
        data = json.loads(request.body)
        cell_index = int(data.get('cell_index'))
    except (json.JSONDecodeError, TypeError, ValueError):
        return JsonResponse({'error': 'Invalid request data.'}, status=400)

    board = game.get_board_state()
    if not (0 <= cell_index < 9 and board[cell_index] is None):
        return JsonResponse({'error': 'Invalid or already taken cell.'}, status=400)

    # Make the move
    board[cell_index] = 'X' if request.user == game.player1 else 'O'
    game.set_board_state(board)

    # Check for winner
    winner_symbol = check_winner(board)
    if winner_symbol:
        if winner_symbol == 'draw':
            game.status = GameSession.STATUS_DRAW
        else:
            game.status = GameSession.STATUS_FINISHED
            game.winner = game.player1 if winner_symbol == 'X' else game.player2
        game.current_turn = None # Game over
    else:
        # Switch turns
        game.current_turn = game.player2 if request.user == game.player1 else game.player1

    game.save()

    return JsonResponse({'status': 'success', 'message': 'Move recorded.'})
