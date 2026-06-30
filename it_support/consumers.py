import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import IT_Ticket, ChatMessage
from accounts.models import User

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.ticket_id = self.scope['url_route']['kwargs']['ticket_id']
        self.ticket_group_name = f'chat_{self.ticket_id}'
        self.user = self.scope['user']

        if not self.user.is_authenticated:
            await self.close()
            return

        is_authorized = await self.check_user_permissions()
        if not is_authorized:
            await self.close()
            return

        await self.channel_layer.group_add(
            self.ticket_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.ticket_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message_text = text_data_json.get('message', '').strip()

        if not message_text:
            return

        new_message = await self.save_message(message_text)

        avatar_url = f'https://ui-avatars.com/api/?name={self.user.username[0]}&background=random&color=fff'
        if self.user.avatar:
            avatar_url = self.user.avatar.url

        await self.channel_layer.group_send(
            self.ticket_group_name,
            {
                'type': 'chat_message',
                'message': new_message.message,
                'author': self.user.username,
                'timestamp': new_message.timestamp.isoformat(),
                'author_avatar_url': avatar_url,
                'attachment_url': None,
                'attachment_name': None,
            }
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'message': event['message'],
            'author': event['author'],
            'timestamp': event['timestamp'],
            'author_avatar_url': event['author_avatar_url'],
            'attachment_url': event.get('attachment_url'),
            'attachment_name': event.get('attachment_name'),
        }))

    @database_sync_to_async
    def check_user_permissions(self):
        try:
            ticket = IT_Ticket.objects.get(id=self.ticket_id)
            if ticket.chat_status != 'active':
                return False
            has_management_access = getattr(self.user, 'has_it_support_management_access', False)
            return (
                ticket.user == self.user
                or ticket.assigned_to == self.user
                or self.user.is_superuser
                or has_management_access
                or self.user.role in [User.SUPERADMIN, User.IT_TECHNICIAN]
            )
        except IT_Ticket.DoesNotExist:
            return False

    @database_sync_to_async
    def save_message(self, message_text):
        ticket = IT_Ticket.objects.get(id=self.ticket_id)
        return ChatMessage.objects.create(
            ticket=ticket,
            author=self.user,
            message=message_text
        )
