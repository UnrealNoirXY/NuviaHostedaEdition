from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from accounts.models import User
from clients.models import Company
from resort.models import Resort, Room
from .models import Ticket
from unittest.mock import patch
from rest_framework.test import APIClient

DJANGO_VITE_TEST_CONFIG = {
    "default": {
        "dev_mode": True,
        "manifest_path": settings.DJANGO_VITE["default"]["manifest_path"],
        "static_url_prefix": settings.DJANGO_VITE["default"].get("static_url_prefix", "/vite/"),
        "app_client_class": settings.DJANGO_VITE["default"].get("app_client_class"),
    }
}

@override_settings(DJANGO_VITE=DJANGO_VITE_TEST_CONFIG)
class TicketSystemTestCase(TestCase):
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
        # Create Company and Resort
        self.company = Company.objects.create(name="Test Hotel Group")
        self.resort = Resort.objects.create(name="Seaside Resort", company=self.company)
        self.room = Room.objects.create(name="101", resort=self.resort)

        # Create Users with different roles
        self.receptionist = User.objects.create_user(
            username='recep', password='password123', role=User.RECEPTIONIST, resort=self.resort, company=self.company
        )
        self.maintainer = User.objects.create_user(
            username='maint', password='password123', role=User.MAINTAINER, resort=self.resort, company=self.company
        )
        self.owner = User.objects.create_user(
            username='owner', password='password123', role=User.OWNER, company=self.company
        )
        self.head_maintainer = User.objects.create_user(
            username='headmaint', password='password123', role=User.HEAD_MAINTAINER, company=self.company
        )
        self.other_user = User.objects.create_user(
            username='other', password='password123', role=User.RECEPTIONIST # a different user
        )
        self.resort2 = Resort.objects.create(name="Lagoon Resort", company=self.company)

        # Create a ticket
        self.ticket = Ticket.objects.create(
            title="Leaky Faucet",
            description="The faucet in room 101 is dripping.",
            created_by=self.receptionist,
            resort=self.resort,
            room=self.room,
            assigned_to=self.maintainer
        )

    def test_receptionist_can_create_ticket(self):
        """ Tests that a receptionist can create a new ticket. """
        self.client.login(username='recep', password='password123')
        create_url = reverse('ticket_create')

        # The form requires 'assigned_to' which might not be set by receptionist
        # Let's assume for now the form allows creation without assignment
        # or we assign to an existing maintainer

        ticket_data = {
            'title': 'New Broken Lamp',
            'description': 'The lamp on the desk is broken.',
            'resort': self.resort.pk,
            'room': self.room.pk,
            'priority': Ticket.PRIORITY_MEDIUM,
            'assigned_to': self.maintainer.pk
        }

        response = self.client.post(create_url, ticket_data)

        # Successful creation should redirect to the detail page
        self.assertEqual(response.status_code, 302)

        new_ticket = Ticket.objects.get(title='New Broken Lamp')
        self.assertIsNotNone(new_ticket)
        self.assertEqual(new_ticket.created_by, self.receptionist)
        self.assertIsNone(new_ticket.due_date)

    def test_head_maintainer_can_set_deadline_on_create(self):
        self.client.login(username='headmaint', password='password123')
        create_url = reverse('ticket_create')
        due_date = (timezone.now() + timezone.timedelta(days=2)).strftime('%Y-%m-%dT%H:%M')

        ticket_data = {
            'title': 'Urgent Boiler Fix',
            'description': 'Boiler needs urgent fix.',
            'resort': self.resort.pk,
            'room': self.room.pk,
            'priority': Ticket.PRIORITY_HIGH,
            'assigned_to': self.maintainer.pk,
            'due_date': due_date,
        }

        response = self.client.post(create_url, ticket_data)
        self.assertEqual(response.status_code, 302)
        ticket = Ticket.objects.get(title='Urgent Boiler Fix')
        self.assertIsNotNone(ticket.due_date)

    def test_cannot_close_without_completion_photo(self):
        self.client.login(username='headmaint', password='password123')
        detail_url = reverse('ticket_detail', kwargs={'ticket_id': self.ticket.pk})
        response = self.client.post(detail_url, {
            'status': 'closed',
            'notes': 'Lavoro completato',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Per chiudere il ticket è obbligatorio caricare una foto del lavoro finito.")

    def test_can_close_with_completion_photo(self):
        self.client.login(username='headmaint', password='password123')
        detail_url = reverse('ticket_detail', kwargs={'ticket_id': self.ticket.pk})
        response = self.client.post(detail_url, {
            'status': 'closed',
            'notes': 'Lavoro completato',
        }, follow=True)
        # Without file should still fail
        self.assertContains(response, "Per chiudere il ticket è obbligatorio caricare una foto del lavoro finito.")

        response = self.client.post(detail_url, {
            'status': 'closed',
            'notes': 'Lavoro completato',
            'completion_photo': SimpleUploadedFile('photo.jpg', b"testimagecontent", content_type='image/jpeg'),
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.ticket.refresh_from_db()
        self.assertIsNotNone(self.ticket.completion_photo)

    def test_ticket_detail_view_permissions(self):
        """ Tests that only relevant users can see a ticket's details. """
        detail_url = reverse('ticket_detail', kwargs={'ticket_id': self.ticket.pk})

        # The creator should be able to see it
        self.client.login(username='recep', password='password123')
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Leaky Faucet")

        # The assigned maintainer should be able to see it
        self.client.login(username='maint', password='password123')
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, 200)

    def test_calendar_filters_respect_resort_permissions(self):
        other_resort = Resort.objects.create(name="Alta Montagna", company=self.company)
        self.client.login(username='maint', password='password123')
        response = self.client.get('/api/maintenance/tickets/calendar/', {'resort': other_resort.id})
        self.assertEqual(response.status_code, 403)

    def test_metadata_includes_permission_map_and_user(self):
        self.client.login(username='owner', password='password123')
        response = self.client.get('/api/maintenance/tickets/metadata/')
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn('permissionMap', payload)
        self.assertTrue(payload['permissionMap']['canCreateTickets'])
        self.assertIn('currentUser', payload)
        self.assertEqual(payload['currentUser']['id'], self.owner.id)

        # The owner of the company should be able to see it
        self.client.login(username='owner', password='password123')
        detail_url = reverse('ticket_detail', kwargs={'ticket_id': self.ticket.pk})
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, 200)

        # Head maintainer with same company should be able to see it
        self.client.login(username='headmaint', password='password123')
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, 200)

        # A random other user should NOT be able to see it
        self.client.login(username='other', password='password123')
        response = self.client.get(detail_url)
        self.assertNotEqual(response.status_code, 200)

    def test_dashboard_views_for_roles(self):
        """ Tests that users see the correct dashboard. """
        # Maintainer dashboard should show the ticket assigned to them
        self.client.login(username='maint', password='password123')
        response = self.client.get(reverse('dashboard_maintainer'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.ticket.title)

        # Create a ticket not assigned to our maintainer
        unassigned_ticket = Ticket.objects.create(
            title="Unassigned", description="...", created_by=self.receptionist, resort=self.resort
        )
        response = self.client.get(reverse('dashboard_maintainer'))
        self.assertNotContains(response, unassigned_ticket.title)

    def test_head_maintainer_can_create_ticket_for_any_resort(self):
        """ Tests that a head maintainer can create a ticket and sees all resorts in their company. """
        self.client.login(username='headmaint', password='password123')
        create_url = reverse('ticket_create')
        response = self.client.get(create_url)
        self.assertEqual(response.status_code, 200)

        # Check that the form's resort queryset contains both resorts from the company
        form = response.context['form']
        resort_queryset = form.fields['resort'].queryset
        self.assertEqual(resort_queryset.count(), 2)
        self.assertIn(self.resort, resort_queryset)
        self.assertIn(self.resort2, resort_queryset)

    def test_maintainer_must_acknowledge_due_date_before_progress(self):
        due_date = timezone.now() + timezone.timedelta(days=1)
        self.ticket.due_date = due_date
        self.ticket.initial_due_date = due_date
        self.ticket.save(update_fields=["due_date", "initial_due_date"])

        self.client.login(username='maint', password='password123')
        detail_url = reverse('ticket_detail', kwargs={'ticket_id': self.ticket.pk})

        response = self.client.post(detail_url, {
            'status': 'in_progress',
            'notes': 'Mi occuperò presto del guasto',
        }, follow=True)

        self.assertContains(response, 'Devi confermare la scadenza', msg_prefix="La conferma scadenza dovrebbe essere obbligatoria.")

        ack_value = timezone.localtime(due_date).strftime('%Y-%m-%dT%H:%M')
        response = self.client.post(detail_url, {
            'status': 'in_progress',
            'notes': 'Mi occuperò presto del guasto',
            'acknowledged_due_date': ack_value,
        }, follow=True)

        self.assertEqual(response.status_code, 200)
        updated_ticket = Ticket.objects.get(pk=self.ticket.pk)
        self.assertIsNotNone(updated_ticket.acknowledged_due_date)
        self.ticket.refresh_from_db()
        self.assertIsNotNone(self.ticket.acknowledged_due_date)
        self.assertEqual(self.ticket.status, 'in_progress')

    def test_calendar_endpoint_includes_ack_status(self):
        due_date = timezone.now() + timezone.timedelta(days=2)
        self.ticket.due_date = due_date
        self.ticket.initial_due_date = due_date
        self.ticket.save(update_fields=["due_date", "initial_due_date"])

        self.client.login(username='headmaint', password='password123')
        response = self.client.get('/api/maintenance/tickets/calendar/')
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn('events', payload)
        event = next((item for item in payload['events'] if item['id'] == self.ticket.id), None)
        self.assertIsNotNone(event, "Il ticket dovrebbe comparire nel calendario")
        self.assertIn('acknowledged', event)
        self.assertFalse(event['acknowledged'])


class TicketApiTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.company = Company.objects.create(name="API Company")
        self.resort = Resort.objects.create(name="API Resort", company=self.company)
        self.room = Room.objects.create(name="201", resort=self.resort)

        self.head = User.objects.create_user(
            username='api-head',
            password='pass123',
            role=User.HEAD_MAINTAINER,
            company=self.company,
            resort=self.resort,
            has_maintenance_access=True,
        )
        self.maintainer = User.objects.create_user(
            username='api-maint',
            password='pass123',
            role=User.MAINTAINER,
            company=self.company,
            resort=self.resort,
            has_maintenance_access=True,
        )
        self.other_same_resort = User.objects.create_user(
            username='api-maint-extra',
            password='pass123',
            role=User.MAINTAINER,
            company=self.company,
            resort=self.resort,
            has_maintenance_access=True,
        )
        self.manager = User.objects.create_user(
            username='api-manager',
            password='pass123',
            role=User.MAINTENANCE_MANAGER,
            company=self.company,
            resort=self.resort,
            has_maintenance_access=True,
        )
        self.superadmin_user = User.objects.create_user(
            username='api-super',
            password='pass123',
            role=User.SUPERADMIN,
            company=self.company,
            resort=self.resort,
            has_maintenance_access=False,
        )
        self.other_resort = Resort.objects.create(name="API Resort 2", company=self.company)
        self.other_maintainer = User.objects.create_user(
            username='api-maint-2',
            password='pass123',
            role=User.MAINTAINER,
            company=self.company,
            resort=self.other_resort,
            has_maintenance_access=True,
        )
        self.receptionist = User.objects.create_user(
            username='api-recep',
            password='pass123',
            role=User.RECEPTIONIST,
            company=self.company,
            resort=self.resort,
            has_maintenance_access=True,
        )

    def authenticate(self, user):
        self.client.force_authenticate(user=user)

    def test_create_ticket_requires_confirmation(self):
        self.authenticate(self.head)
        url = '/api/maintenance/tickets/'
        payload = {
            'title': 'API Leak',
            'description': 'Test leak',
            'resort': self.resort.id,
            'room': self.room.id,
            'priority': Ticket.PRIORITY_HIGH,
            'assigned_to': self.maintainer.id,
            'due_date': (timezone.now() + timezone.timedelta(days=1)).isoformat(),
        }

        response = self.client.post(url, payload, format='multipart')
        self.assertEqual(response.status_code, 400)

        payload['confirmed'] = True
        response = self.client.post(url, payload, format='multipart')
        self.assertEqual(response.status_code, 201)
        ticket = Ticket.objects.get(title='API Leak')
        self.assertEqual(ticket.claimed_by, self.maintainer)
        self.assertIsNotNone(ticket.first_claimed_at)

    def test_superadmin_role_can_create_ticket_via_api_even_without_explicit_access_flag(self):
        client = APIClient()
        client.force_authenticate(user=self.superadmin_user)

        payload = {
            'title': 'Elevator inspection',
            'description': 'Programmare controllo cabina',
            'resort': self.resort.id,
            'room': self.room.id,
            'priority': Ticket.PRIORITY_MEDIUM,
            'confirmed': True,
            'notification_mode': 'selected',
            'notify_maintainers': [self.maintainer.id],
        }

        response = client.post('/api/maintenance/tickets/', payload, format='multipart')

        self.assertEqual(response.status_code, 201)
        ticket = Ticket.objects.get(title='Elevator inspection')
        self.assertEqual(ticket.created_by, self.superadmin_user)

    def test_create_ticket_rejects_assignee_outside_resort(self):
        self.authenticate(self.head)
        url = '/api/maintenance/tickets/'
        payload = {
            'title': 'API Wrong Assignee',
            'description': 'Assegna fuori resort',
            'resort': self.resort.id,
            'room': self.room.id,
            'priority': Ticket.PRIORITY_HIGH,
            'assigned_to': self.other_maintainer.id,
            'confirmed': True,
        }

        response = self.client.post(url, payload, format='multipart')
        self.assertEqual(response.status_code, 400)

    def test_create_ticket_rejects_assignee_not_maintainer(self):
        self.authenticate(self.head)
        url = '/api/maintenance/tickets/'
        payload = {
            'title': 'API Wrong Role',
            'description': 'Assegna ruolo non manutentore',
            'resort': self.resort.id,
            'room': self.room.id,
            'priority': Ticket.PRIORITY_HIGH,
            'assigned_to': self.receptionist.id,
            'confirmed': True,
        }

        response = self.client.post(url, payload, format='multipart')
        self.assertEqual(response.status_code, 400)

    def test_claim_and_release_ticket(self):
        ticket = Ticket.objects.create(
            title='Loose door',
            description='Door hinge is loose',
            resort=self.resort,
            created_by=self.head,
            status='open',
        )

        self.authenticate(self.maintainer)
        claim_url = f'/api/maintenance/tickets/{ticket.id}/claim/'
        response = self.client.post(claim_url)
        self.assertEqual(response.status_code, 200)
        ticket.refresh_from_db()
        self.assertEqual(ticket.assigned_to, self.maintainer)
        self.assertEqual(ticket.claimed_by, self.maintainer)

        release_url = f'/api/maintenance/tickets/{ticket.id}/release/'
        response = self.client.post(release_url)
        self.assertEqual(response.status_code, 200)
        ticket.refresh_from_db()
        self.assertIsNone(ticket.assigned_to)
        self.assertIsNone(ticket.claimed_by)
        self.assertIsNotNone(ticket.last_released_at)

    def test_release_requires_assignment_or_privilege(self):
        ticket = Ticket.objects.create(
            title='Boiler check',
            description='Routine check',
            resort=self.resort,
            created_by=self.head,
            assigned_to=self.other_same_resort,
            status='open',
        )

        self.authenticate(self.maintainer)
        release_url = f'/api/maintenance/tickets/{ticket.id}/release/'
        response = self.client.post(release_url)
        self.assertEqual(response.status_code, 404)

    def test_create_ticket_requires_assignee_or_selected_notifications(self):
        self.authenticate(self.head)
        url = '/api/maintenance/tickets/'
        payload = {
            'title': 'API no assignee',
            'description': 'Missing assignee',
            'resort': self.resort.id,
            'room': self.room.id,
            'priority': Ticket.PRIORITY_MEDIUM,
            'confirmed': True,
            'notification_mode': 'assigned',
        }

        response = self.client.post(url, payload, format='multipart')
        self.assertEqual(response.status_code, 400)

        payload['notification_mode'] = 'selected'
        payload['notify_maintainers'] = [self.maintainer.id]
        response = self.client.post(url, payload, format='multipart')
        self.assertEqual(response.status_code, 201)

    def test_unassigned_alert_preference(self):
        self.authenticate(self.manager)
        url = '/api/maintenance/tickets/preferences/unassigned-alerts/'
        response = self.client.post(url, {'enabled': False})
        self.assertEqual(response.status_code, 200)
        self.manager.refresh_from_db()
        self.assertFalse(self.manager.receives_unassigned_ticket_alerts)

    def test_insights_endpoint(self):
        Ticket.objects.create(
            title='Free ticket',
            resort=self.resort,
            created_by=self.head,
            status='open',
            due_date=timezone.now() + timezone.timedelta(hours=2),
        )

        self.authenticate(self.head)
        url = '/api/maintenance/tickets/insights/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('unassigned', data)
        self.assertGreaterEqual(data['unassigned']['total'], 1)
