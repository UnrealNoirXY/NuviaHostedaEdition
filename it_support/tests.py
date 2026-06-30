from django.test import TestCase
from django.urls import reverse
from accounts.models import User
from assets.models import Asset, AssetCategory
from resort.models import Resort
from .models import IT_Ticket
from decimal import Decimal

class ITSupportFormTestCase(TestCase):
    def setUp(self):
        self.resort1 = Resort.objects.create(name='Resort A')
        self.resort2 = Resort.objects.create(name='Resort B')
        self.user1 = User.objects.create_user(username='user1', password='password123', resort=self.resort1)
        category = AssetCategory.objects.create(name='Printers')
        self.asset1 = Asset.objects.create(name='Printer Lobby A', category=category, resort=self.resort1)
        self.asset2 = Asset.objects.create(name='Printer Office B', category=category, resort=self.resort2)
        self.unassigned_asset = Asset.objects.create(name='Unassigned Laptop', category=category, resort=None)

    def test_asset_dropdown_is_filtered_by_resort(self):
        self.client.login(username='user1', password='password123')
        response = self.client.get(reverse('it_support:it_ticket_create'))
        self.assertEqual(response.status_code, 200)
        form = response.context.get('form')
        self.assertIsNotNone(form)
        assets_in_dropdown = form.fields['asset'].queryset
        self.assertIn(self.asset1, assets_in_dropdown)
        self.assertIn(self.unassigned_asset, assets_in_dropdown)
        self.assertNotIn(self.asset2, assets_in_dropdown)
        self.assertEqual(assets_in_dropdown.count(), 2)

class ITSupportUpdateTestCase(TestCase):
    def setUp(self):
        self.technician = User.objects.create_user(username='tech', password='password123', role=User.IT_TECHNICIAN)
        self.user = User.objects.create_user(username='regularuser', password='password123')
        self.ticket = IT_Ticket.objects.create(user=self.user, title='Test Ticket')

    def test_technician_can_add_intervention_cost(self):
        self.client.login(username='tech', password='password123')
        update_url = reverse('it_support:it_ticket_update', kwargs={'pk': self.ticket.pk})

        update_data = {
            'status': self.ticket.status,
            'priority': self.ticket.priority,
            'assigned_to': self.technician.pk,
            'intervention_cost': '99.50'
        }

        response = self.client.post(update_url, update_data)
        self.assertRedirects(response, reverse('it_support:it_ticket_detail', kwargs={'pk': self.ticket.pk}))

        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.intervention_cost, Decimal('99.50'))


import json
from channels.testing import WebsocketCommunicator
from channels.db import database_sync_to_async
from channels.layers import get_channel_layer
from gestione_manutenzioni.asgi import application
from .models import ChatMessage

class ChatConsumerTestCase(TestCase):

    @database_sync_to_async
    def create_user(self, username, password, role=User.RECEPTIONIST):
        return User.objects.create_user(username=username, password=password, role=role)

    @database_sync_to_async
    def create_ticket(self, user, title, chat_status='none'):
        return IT_Ticket.objects.create(user=user, title=title, chat_status=chat_status)

    @database_sync_to_async
    def get_message_count(self, ticket):
        return ChatMessage.objects.filter(ticket=ticket).count()

    async def test_authorized_user_can_connect_to_active_chat(self):
        user = await self.create_user('consumeruser', 'password123')
        ticket = await self.create_ticket(user, "Consumer Test Ticket", chat_status='active')

        communicator = WebsocketCommunicator(application, f"/ws/chat/{ticket.pk}/")
        communicator.scope['user'] = user
        connected, _ = await communicator.connect()
        self.assertTrue(connected, "Authorized user should be able to connect to an active chat.")
        await communicator.disconnect()

    async def test_user_cannot_connect_to_inactive_chat(self):
        user = await self.create_user('consumeruser', 'password123')
        ticket = await self.create_ticket(user, "Consumer Test Ticket", chat_status='ended')

        communicator = WebsocketCommunicator(application, f"/ws/chat/{ticket.pk}/")
        communicator.scope['user'] = user
        connected, _ = await communicator.connect()
        self.assertFalse(connected, "User should not be able to connect to an inactive chat.")

    async def test_unauthorized_user_is_rejected(self):
        user = await self.create_user('mainuser', 'password123')
        ticket = await self.create_ticket(user, "Another Ticket", chat_status='active')
        unauthorized_user = await self.create_user('unauthorized', 'password123')

        communicator = WebsocketCommunicator(application, f"/ws/chat/{ticket.pk}/")
        communicator.scope['user'] = unauthorized_user
        connected, _ = await communicator.connect()
        self.assertFalse(connected, "Unauthorized user should be rejected.")

    async def test_unauthenticated_user_is_rejected(self):
        user = await self.create_user('dummyuser', 'password123')
        ticket = await self.create_ticket(user, "Ticket for Anon Test", chat_status='active')

        from django.contrib.auth.models import AnonymousUser
        communicator = WebsocketCommunicator(application, f"/ws/chat/{ticket.pk}/")
        communicator.scope['user'] = AnonymousUser()
        connected, _ = await communicator.connect()
        self.assertFalse(connected, "Unauthenticated user should be rejected.")

    async def test_can_send_and_receive_message(self):
        user = await self.create_user('msg_sender', 'password123')
        ticket = await self.create_ticket(user, "Message Sending Test", chat_status='active')

        communicator = WebsocketCommunicator(application, f"/ws/chat/{ticket.pk}/")
        communicator.scope['user'] = user
        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        # Send a message
        await communicator.send_json_to({'message': 'Hello from the test!'})

        # The consumer should broadcast it back to us
        response = await communicator.receive_json_from()
        self.assertEqual(response['message'], 'Hello from the test!')
        self.assertEqual(response['author'], user.username)

        # Verify the message was saved in the database
        count = await self.get_message_count(ticket)
        self.assertEqual(count, 1)

        await communicator.disconnect()
