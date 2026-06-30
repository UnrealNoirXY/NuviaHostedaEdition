from django.conf import settings
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model
from resort.models import Resort, Room
from clients.models import Company
from tickets.models import Ticket
from unittest.mock import patch

User = get_user_model()

DJANGO_VITE_TEST_CONFIG = {
    "default": {
        "dev_mode": True,
        "manifest_path": settings.DJANGO_VITE["default"]["manifest_path"],
        "static_url_prefix": settings.DJANGO_VITE["default"].get("static_url_prefix", "/vite/"),
        "app_client_class": settings.DJANGO_VITE["default"].get("app_client_class"),
    }
}

@override_settings(DJANGO_VITE=DJANGO_VITE_TEST_CONFIG)
class TicketWorkflowTest(TestCase):
    """
    Tests the full workflow for ticket creation and viewing.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._vite_patcher = patch('django_vite.templatetags.django_vite.DjangoViteAssetLoader.instance')
        cls._vite_instance_mock = cls._vite_patcher.start()
        cls._vite_instance_mock.return_value.generate_vite_asset.return_value = ""

    @classmethod
    def tearDownClass(cls):
        cls._vite_patcher.stop()
        super().tearDownClass()

    def setUp(self):
        """Set up the necessary objects for the tests."""
        self.client = Client()
        self.company = Company.objects.create(name="Test Company")
        self.resort = Resort.objects.create(name="Test Resort", company=self.company)
        self.room = Room.objects.create(name="Room 101", resort=self.resort)

        # Create a user who can create tickets
        self.creator_password = 'password123'
        self.creator_user = User.objects.create_user(
            username='receptionist_user',
            password=self.creator_password,
            role=User.RECEPTIONIST,
            company=self.company,
            resort=self.resort
        )

    def test_receptionist_can_create_and_view_ticket(self):
        """
        Verify that a user with the RECEPTIONIST role can successfully
        create a ticket and then view its detail page.
        """
        # 1. Login as the receptionist
        login_successful = self.client.login(
            username=self.creator_user.username,
            password=self.creator_password
        )
        self.assertTrue(login_successful, "Client login failed.")

        # 2. Prepare the data for the ticket creation form
        ticket_data = {
            'title': 'Leaking Faucet',
            'resort': self.resort.id,
            'room': self.room.id,
            'priority': Ticket.PRIORITY_MEDIUM,
            'description': 'The faucet in the bathroom is leaking constantly.'
        }

        # 3. Make a POST request to the ticket creation view
        create_url = reverse('ticket_create')
        response = self.client.post(create_url, data=ticket_data)

        # 4. Check that a ticket was created in the database
        self.assertEqual(Ticket.objects.count(), 1, "Ticket was not created in the database.")
        new_ticket = Ticket.objects.first()
        self.assertEqual(new_ticket.title, 'Leaking Faucet')
        self.assertEqual(new_ticket.created_by, self.creator_user)

        # 5. Check that the response is a redirect to the detail page
        self.assertEqual(response.status_code, 302, "Response was not a redirect.")
        expected_redirect_url = reverse('ticket_detail', args=[new_ticket.id])
        self.assertRedirects(response, expected_redirect_url, msg_prefix="Redirected to wrong URL.")

        # 6. Follow the redirect and check the detail page
        detail_response = self.client.get(expected_redirect_url)
        self.assertEqual(detail_response.status_code, 200, "Ticket detail page did not load correctly.")
        self.assertContains(detail_response, 'Leaking Faucet', msg_prefix="Ticket title not found on detail page.")
        self.assertContains(detail_response, 'The faucet in the bathroom is leaking constantly.', msg_prefix="Ticket description not found on detail page.")
