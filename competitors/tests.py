from django.test import TestCase, override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model
from unittest.mock import patch

from .models import Competitor, ScrapingLink, ScrapedData, ResortCompetitorAssociation
from clients.models import Company
from resort.models import Resort
from reviews.models import ReviewSource

User = get_user_model()

class CompetitorViewTests(TestCase):

    def setUp(self):
        self.company = Company.objects.create(name="Test Company")
        self.super_admin = User.objects.create_superuser(
            username='superadmin', email='super@admin.com', password='password'
        )
        self.director = User.objects.create_user(
            username='director', password='password', role='director', company=self.company
        )
        self.resort = Resort.objects.create(name="Test Resort", company=self.company)
        self.director.resort = self.resort
        self.director.save()
        self.competitor = Competitor.objects.create(name="Test Competitor", company=self.company)
        self.list_url = reverse('competitors:competitor-list')
        self.create_url = reverse('competitors:competitor-create')
        self.update_url = reverse('competitors:competitor-update', args=[self.competitor.pk])
        self.delete_url = reverse('competitors:competitor-delete', args=[self.competitor.pk])

    def test_superuser_can_access_list_view(self):
        self.client.login(username='superadmin', password='password')
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 200)

    def test_director_is_forbidden_from_management(self):
        self.client.login(username='director', password='password')
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 403)

    def test_competitor_create_view_post_by_superuser(self):
        self.client.login(username='superadmin', password='password')
        data = {'name': 'New Competitor', 'website': 'https://new.com', 'company': self.company.pk}
        response = self.client.post(self.create_url, data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Competitor.objects.filter(name='New Competitor').exists())

    def test_manage_links_modal_view_post_htmx_with_detailed_options(self):
        """Test adding a link with the new detailed form fields."""
        self.client.login(username='superadmin', password='password')
        source, _ = ReviewSource.objects.get_or_create(name="Booking.com")
        modal_url = reverse('competitors:manage-links-modal', args=[self.competitor.pk])
        data = {
            'source': source.pk,
            'url': 'https://htmx-test.com',
            'max_reviews_booking': '150', # Use the new specific field
            'max_reviews_google': '', # Ensure empty fields are handled
            'max_reviews_tripadvisor': '',
        }
        response = self.client.post(modal_url, data, HTTP_HX_REQUEST='true')

        self.assertEqual(response.status_code, 200)
        self.assertTrue(ScrapingLink.objects.filter(url='https://htmx-test.com').exists())

        saved_link = ScrapingLink.objects.get(url='https://htmx-test.com')
        self.assertIn('maxReviewsPerHotel', saved_link.platform_options)
        self.assertEqual(saved_link.platform_options['maxReviewsPerHotel'], 150)
        self.assertNotIn('maxReviews', saved_link.platform_options) # Check that other keys are not added

    def test_delete_scraping_link_htmx(self):
        self.client.login(username='superadmin', password='password')
        source, _ = ReviewSource.objects.get_or_create(name="Test Source")
        link_to_delete = ScrapingLink.objects.create(competitor=self.competitor, source=source, url='https://to-delete.com')
        delete_url = reverse('competitors:delete-scraping-link', args=[link_to_delete.pk])
        response = self.client.post(delete_url, HTTP_HX_REQUEST='true')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(ScrapingLink.objects.filter(pk=link_to_delete.pk).exists())

    def test_manage_associations_view_get(self):
        self.client.login(username='superadmin', password='password')
        url = reverse('competitors:manage-associations', kwargs={'resort_pk': self.resort.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_manage_associations_view_post(self):
        self.client.login(username='superadmin', password='password')
        url = reverse('competitors:manage-associations', kwargs={'resort_pk': self.resort.pk})
        competitor_to_add = Competitor.objects.create(name="Another Competitor", company=self.company)
        data = {'competitor': competitor_to_add.pk}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(ResortCompetitorAssociation.objects.filter(resort=self.resort, competitor=competitor_to_add).exists())

    def test_remove_association_view(self):
        """Test that a superuser can remove an association."""
        self.client.login(username='superadmin', password='password')
        assoc = ResortCompetitorAssociation.objects.create(resort=self.resort, competitor=self.competitor)
        self.assertTrue(ResortCompetitorAssociation.objects.filter(pk=assoc.pk).exists())
        url = reverse('competitors:remove-association', kwargs={'pk': assoc.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(ResortCompetitorAssociation.objects.filter(pk=assoc.pk).exists())

    @patch('competitors.views.trigger_competitor_scraping')
    def test_scraping_panel_view_post(self, mock_trigger_scraping):
        self.client.login(username='superadmin', password='password')
        url = reverse('competitors:scraping-panel')
        source, _ = ReviewSource.objects.get_or_create(name="Panel Test Source")
        link = ScrapingLink.objects.create(competitor=self.competitor, source=source, url='https://panel-test.com', is_active=True)
        data = {'competitors': [self.competitor.pk]}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        mock_trigger_scraping.assert_called_once_with(scraping_link_ids=[link.id])


class ScrapingServiceTests(TestCase):
    def test_sentiment_analysis_signal(self):
        """Test that the post_save signal correctly triggers sentiment analysis."""
        source, _ = ReviewSource.objects.get_or_create(name="Signal Test Source")
        competitor = Competitor.objects.create(name="Signal Competitor", company=Company.objects.create(name="Signal Co"))
        link = ScrapingLink.objects.create(competitor=competitor, source=source, url='https://signal-test.com')

        # Creating this object should trigger the signal
        scraped_data = ScrapedData.objects.create(
            scraping_link=link,
            source_identifier='signal-123',
            text='This is a great place!',
            rating=5.0
        )

        # Check that the analysis object was created
        self.assertTrue(hasattr(scraped_data, 'analysis'))
        self.assertEqual(scraped_data.analysis.sentiment_label, 'positive')

    # ... (omitting for brevity)
    def setUp(self):
        self.company = Company.objects.create(name="Service Test Co")
        self.source, _ = ReviewSource.objects.get_or_create(name="Test Platform", defaults={'scraper_identifier': "test/actor"})
        self.competitor = Competitor.objects.create(name="Service Competitor", company=self.company)
        self.scraping_link = ScrapingLink.objects.create(competitor=self.competitor, source=self.source, url="https://test.com/hotel", platform_options={'maxReviews': 75})

    @override_settings(APIFY_API_TOKEN='test-token')
    @patch('competitors.services.ApifyClientWrapper')
    def test_trigger_competitor_scraping_service(self, MockApifyClientWrapper):
        mock_instance = MockApifyClientWrapper.return_value
        mock_instance.start_scraper.return_value = {'defaultDatasetId': 'mock_dataset_id'}
        mock_results = [{'id': '12345'}]
        mock_instance.get_run_results.return_value = mock_results
        from .services import trigger_competitor_scraping
        trigger_competitor_scraping(scraping_link_ids=[self.scraping_link.id])
        mock_instance.start_scraper.assert_called_once()
        called_args, _ = mock_instance.start_scraper.call_args
        run_input_arg = called_args[1]
        self.assertEqual(run_input_arg['maxReviews'], 75)
