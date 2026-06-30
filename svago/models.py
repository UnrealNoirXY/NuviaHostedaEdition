from django.db import models
from accounts.models import User
import json

class GameSession(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_ACTIVE = 'active'
    STATUS_FINISHED = 'finished'
    STATUS_DRAW = 'draw'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'In attesa'),
        (STATUS_ACTIVE, 'In corso'),
        (STATUS_FINISHED, 'Terminata'),
        (STATUS_DRAW, 'Pareggio'),
    ]

    player1 = models.ForeignKey(User, on_delete=models.CASCADE, related_name='games_as_player1')
    player2 = models.ForeignKey(User, on_delete=models.CASCADE, related_name='games_as_player2')

    # The board state will be stored as a JSON string representing a list of 9 elements (null, 'X', or 'O')
    board_state = models.CharField(max_length=255, default='[null, null, null, null, null, null, null, null, null]')

    current_turn = models.ForeignKey(User, on_delete=models.CASCADE, related_name='current_games')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_PENDING)
    winner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='won_games')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def get_board_state(self):
        return json.loads(self.board_state)

    def set_board_state(self, board):
        self.board_state = json.dumps(board)

    def __str__(self):
        return f"Game between {self.player1.username} and {self.player2.username} ({self.get_status_display()})"
