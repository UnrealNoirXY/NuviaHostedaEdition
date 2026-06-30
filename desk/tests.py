from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from communications.models import Announcement
from tickets.models import Ticket
from reviews.models import Review, ReviewAnalysis
from .models import WidgetPreference
from desk.widget_config import ROLE_WIDGET_MAP
from django.utils import timezone
import datetime
import json

User = get_user_model()

class DeskViewsTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='password123', role='receptionist')
        self.maintainer = User.objects.create_user(username='maintainer', password='password123', role='maintainer')

        # Create some test data
        Announcement.objects.create(title="Test Announcement", body="Test body content", author=self.user)
        # We need a resort to create a ticket
        from resort.models import Resort
        resort = Resort.objects.create(name="Test Resort", location="Test Location")

        Ticket.objects.create(
            title="Test Ticket",
            description="Test description",
            created_by=self.user,
            resort=resort,
            due_date=timezone.now() + datetime.timedelta(days=1),
            assigned_to=self.maintainer
        )
        Ticket.objects.create(
            title="Another Ticket",
            description="Another description",
            created_by=self.user,
            resort=resort,
            status='resolved'
        )

    def test_home_desk_view_authenticated(self):
        self.client.login(username='testuser', password='password123')
        response = self.client.get(reverse('desk:home'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'desk/nuvia_os.html')
        self.assertIn('recent_announcements', response.context)
        self.assertEqual(len(response.context['recent_announcements']), 1)

    def test_home_desk_view_unauthenticated(self):
        response = self.client.get(reverse('desk:home'))
        self.assertEqual(response.status_code, 302) # Redirects to login
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('desk:home')}")

    def test_home_desk_view_for_maintainer(self):
        self.client.login(username='maintainer', password='password123')
        response = self.client.get(reverse('desk:home'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('maintainer_tickets', response.context)
        self.assertEqual(len(response.context['maintainer_tickets']), 1)
        self.assertEqual(response.context['maintainer_tickets'][0].title, "Test Ticket")

    def test_home_desk_view_for_non_maintainer(self):
        self.client.login(username='testuser', password='password123')
        response = self.client.get(reverse('desk:home'))
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('maintainer_tickets', response.context)

    def test_calendar_events_api_authenticated(self):
        self.client.login(username='testuser', password='password123')
        response = self.client.get(reverse('desk:calendar_events'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['title'], 'Ticket #1: Test Ticket')

    def test_calendar_events_api_unauthenticated(self):
        response = self.client.get(reverse('desk:calendar_events'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('desk:calendar_events')}")


class DeskLayoutTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='layoutuser', password='password123')
        self.url = reverse('desk:save_layout')
        self.client.login(username='layoutuser', password='password123')

    def test_save_layout_creates_preference(self):
        self.assertFalse(WidgetPreference.objects.filter(user=self.user).exists())

        layout_data = [{'id': 'calendar-widget', 'x': 0, 'y': 0, 'w': 8, 'h': 4}]
        response = self.client.post(
            self.url,
            json.dumps({'layout': layout_data}),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'success')
        self.assertTrue(WidgetPreference.objects.filter(user=self.user).exists())

        preference = WidgetPreference.objects.get(user=self.user)
        self.assertEqual(preference.layout, layout_data)

    def test_save_layout_updates_preference(self):
        # Create an initial preference
        WidgetPreference.objects.create(user=self.user, layout=[{'id': 'old-widget'}])

        new_layout_data = [{'id': 'new-widget', 'x': 1, 'y': 1}]
        response = self.client.post(
            self.url,
            json.dumps({'layout': new_layout_data}),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)
        self.user.widget_preference.refresh_from_db()
        self.assertEqual(self.user.widget_preference.layout, new_layout_data)

    def test_home_desk_view_loads_layout(self):
        layout_data = [{'id': 'test-widget'}]
        WidgetPreference.objects.create(user=self.user, layout=layout_data)

        response = self.client.get(reverse('desk:home'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('widget_layout', response.context)
        self.assertEqual(response.context['widget_layout'], json.dumps(layout_data))

    def test_save_layout_invalid_json(self):
        response = self.client.post(
            self.url,
            'this is not json',
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['message'], 'Invalid JSON.')

    def test_save_layout_unauthenticated(self):
        self.client.logout()
        response = self.client.post(
            self.url,
            json.dumps({'layout': []}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 302) # Redirect to login

    def test_home_desk_generates_default_layout(self):
        """
        Test that a user with no saved preferences gets a default layout.
        """
        # 'testuser' is a receptionist and has no WidgetPreference object
        self.client.login(username='testuser', password='password123')
        response = self.client.get(reverse('desk:home'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('widget_layout', response.context)

        layout_data = json.loads(response.context['widget_layout'])
        self.assertIsInstance(layout_data, list)
        self.assertGreater(len(layout_data), 0) # Should not be empty
        # Check if it looks like a widget layout
        self.assertIn('id', layout_data[0])
        self.assertIn('x', layout_data[0])


class DeskDirectorWidgetsTest(TestCase):
    def setUp(self):
        self.client = Client()
        from resort.models import Resort
        self.resort = Resort.objects.create(name="Test Resort", location="Test Location")
        self.director = User.objects.create_user(
            username='director',
            password='password123',
            role='director',
            resort=self.resort
        )
        self.client.login(username='director', password='password123')

        # Create test data
        from reviews.models import ReviewSource
        source = ReviewSource.objects.create(name="Test Source")
        Ticket.objects.create(title="Open Ticket", resort=self.resort, status='open', created_by=self.director)
        Review.objects.create(
            resort=self.resort,
            source=source,
            rating=4.5,
            review_date=timezone.now(),
            review_id='123'
        )
        # The ReviewAnalysis object is created automatically by a signal,
        # so we don't need to create it manually here. We just need to
        # ensure the review object has the analysis attached.
        review = Review.objects.first()
        # If the analysis is not created by the signal for some reason in the test environment,
        # we can create it defensively.
        if not hasattr(review, 'analysis'):
            ReviewAnalysis.objects.create(review=review, sentiment_label='positive', sentiment_score=0.8)
        else:
            # We can update the score if we need a specific value for the test
            review.analysis.sentiment_score = 0.8
            review.analysis.save()


    def test_director_kpis_are_calculated(self):
        response = self.client.get(reverse('desk:home'))
        self.assertEqual(response.status_code, 200)

        self.assertIn('director_kpis', response.context)
        kpis = response.context['director_kpis']
        self.assertEqual(kpis['open_tickets'], 1)
        self.assertEqual(kpis['avg_rating_month'], 4.5)
        self.assertAlmostEqual(kpis['avg_sentiment'], 0.8)

    def test_director_review_chart_data_is_present(self):
        response = self.client.get(reverse('desk:home'))
        self.assertEqual(response.status_code, 200)

        self.assertIn('review_chart_data', response.context)
        chart_data = json.loads(response.context['review_chart_data'])
        self.assertEqual(len(chart_data['labels']), 1)
        self.assertEqual(len(chart_data['data']), 1)
        self.assertEqual(chart_data['data'][0], 4.5)


class DeskRoleWidgetViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        from resort.models import Resort
        self.resort = Resort.objects.create(name="Global Test Resort")

        # Create a user for each role to be tested
        self.superadmin = User.objects.create_user(
            username='superadmin', password='password123', role='superadmin', is_superuser=True
        )
        self.head_maintainer = User.objects.create_user(
            username='headmaintainer', password='password123', role='head_maintainer', resort=self.resort
        )
        self.receptionist = User.objects.create_user(
            username='receptionist', password='password123', role='receptionist', resort=self.resort
        )
        self.owner = User.objects.create_user(
            username='owner', password='password123', role='owner'
        )
        self.housekeeping = User.objects.create_user(
            username='housekeeping', password='password123', role='housekeeping', resort=self.resort
        )
        self.administrative = User.objects.create_user(
            username='administrative', password='password123', role='administrative'
        )
        self.economo = User.objects.create_user(
            username='economo', password='password123', role='economo'
        )
        self.it_technician = User.objects.create_user(
            username='ittechnician', password='password123', role='it_technician'
        )
        self.capo_economo = User.objects.create_user(
            username='capo_economo', password='password123', role='capo_economo'
        )

    def test_superadmin_widgets_and_context(self):
        """
        Ensure a superadmin gets the correct widgets and context data.
        """
        self.client.login(username='superadmin', password='password123')
        response = self.client.get(reverse('desk:home'))
        self.assertEqual(response.status_code, 200)

        # Check for correct widgets
        available_widgets = [w['id'] for w in response.context['available_widgets']]
        expected_widgets = ROLE_WIDGET_MAP.get('all', []) + ROLE_WIDGET_MAP.get('superadmin', [])
        for widget_key in expected_widgets:
            self.assertIn(f"{widget_key.replace('_', '-')}-widget", available_widgets)

        # Check for specific context data
        self.assertIn('ticket_overview', response.context)
        self.assertIn('active_users', response.context)
        self.assertIn('recent_reviews', response.context)
        self.assertIn('system_status', response.context)

    def test_head_maintainer_widgets_and_context(self):
        """
        Ensure a head_maintainer gets the correct widgets and context data.
        """
        self.client.login(username='headmaintainer', password='password123')
        response = self.client.get(reverse('desk:home'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('unassigned_tickets', response.context)
        self.assertIn('urgent_tickets', response.context)
        self.assertIn('critical_stock_items', response.context)
        self.assertIn('team_performance', response.context)

    def test_receptionist_widgets_and_context(self):
        """
        Ensure a receptionist gets the correct widgets and context data.
        """
        self.client.login(username='receptionist', password='password123')
        response = self.client.get(reverse('desk:home'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('quick_ticket_form', response.context)
        self.assertIn('resort_recent_tickets', response.context)
        self.assertIn('guest_announcements', response.context)
        self.assertIn('useful_documents', response.context)

    def test_owner_widgets_and_context(self):
        """
        Ensure an owner gets the correct widgets and context data.
        """
        self.client.login(username='owner', password='password123')
        response = self.client.get(reverse('desk:home'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('financial_performance', response.context)
        self.assertIn('online_reputation', response.context)
        self.assertIn('competitor_analysis', response.context)
        self.assertIn('director_kpis', response.context) # Also gets director KPIs

    def test_housekeeping_widgets_and_context(self):
        """
        Ensure housekeeping gets the correct widgets and context data.
        """
        self.client.login(username='housekeeping', password='password123')
        response = self.client.get(reverse('desk:home'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('rooms_with_status', response.context)
        self.assertIn('quick_report_form', response.context)

    def test_administrative_widgets_and_context(self):
        """
        Ensure administrative gets the correct widgets and context data.
        """
        self.client.login(username='administrative', password='password123')
        response = self.client.get(reverse('desk:home'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('approved_pos', response.context)
        self.assertIn('supplier_list', response.context)
        self.assertIn('useful_documents', response.context)

    def test_economo_widgets_and_context(self):
        """
        Ensure economo gets the correct widgets and context data.
        """
        self.client.login(username='economo', password='password123')
        response = self.client.get(reverse('desk:home'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('critical_stock_items', response.context)
        self.assertIn('supplier_list', response.context)
        self.assertNotIn('po_approvals', response.context) # Should not see this

    def test_it_technician_widgets_and_context(self):
        """
        Ensure it_technician gets the correct widgets and context data.
        """
        self.client.login(username='ittechnician', password='password123')
        response = self.client.get(reverse('desk:home'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('it_tickets', response.context)
        self.assertIn('active_chats', response.context)
        self.assertIn('system_status', response.context)
