from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from accounts.models import User
from clients.models import Company
from resort.models import Resort
from .models import Review, ReviewAnalysis, ReviewSource, ScrapingURL

class ReviewDashboardScopingTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.company1 = Company.objects.create(name="Company A")
        self.company2 = Company.objects.create(name="Company B")
        self.resort1 = Resort.objects.create(name="Resort A", company=self.company1)
        self.resort2 = Resort.objects.create(name="Resort B", company=self.company2)
        self.source = ReviewSource.objects.create(name="Test Source Dashboard", scraper_identifier="test/scraper_dashboard")

        self.owner1 = User.objects.create_user(
            username='owner1', password='password', role=User.OWNER, company=self.company1
        )
        self.review1 = Review.objects.create(resort=self.resort1, source=self.source, rating=5, title="Great Stay", review_date=timezone.now(), review_id="dashboard_1")
        self.review2 = Review.objects.create(resort=self.resort2, source=self.source, rating=1, title="Bad Stay", review_date=timezone.now(), review_id="dashboard_2")

        # The sentiment analysis is now triggered by a signal, so we don't need to create it manually.
        # We just need to get the created analysis objects.
        self.review1.refresh_from_db()
        self.review2.refresh_from_db()

        self.superuser = User.objects.create_superuser(username='superuser', password='password')

    def test_owner_sees_only_their_company_reviews(self):
        self.client.login(username='owner1', password='password')
        response = self.client.get(reverse('reviews:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_reviews'], 1)
        self.assertContains(response, "Great Stay")
        self.assertNotContains(response, "Bad Stay")

    def test_superuser_can_filter_by_company(self):
        self.client.login(username='superuser', password='password')
        response = self.client.get(reverse('reviews:dashboard') + f'?company_id={self.company1.id}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_reviews'], 1)

    def test_receptionist_cannot_access_reviews(self):
        receptionist = User.objects.create_user(username='recep', password='password', role=User.RECEPTIONIST, company=self.company1)
        self.client.login(username='recep', password='password')
        response = self.client.get(reverse('reviews:dashboard'))
        self.assertNotEqual(response.status_code, 200)

class NewRolesReviewAccessTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.company1 = Company.objects.create(name="Company C")
        self.company2 = Company.objects.create(name="Company D")
        self.resort1 = Resort.objects.create(name="Resort C", company=self.company1)
        self.resort2 = Resort.objects.create(name="Resort D", company=self.company2)
        self.source = ReviewSource.objects.create(name="Test Source New Roles", scraper_identifier="test/scraper_new_roles")

        self.review_c = Review.objects.create(resort=self.resort1, source=self.source, rating=5, title="Stay C", review_date=timezone.now(), review_id="new_role_1")
        self.review_d = Review.objects.create(resort=self.resort2, source=self.source, rating=1, title="Stay D", review_date=timezone.now(), review_id="new_role_2")

        self.corporate_user = User.objects.create_user(
            username='corporate_user', password='password', role=User.CORPORATE, company=self.company1
        )
        self.hr_user = User.objects.create_user(
            username='hr_user', password='password', role=User.RISORSE_UMANE, company=self.company1
        )
        self.head_finance_user = User.objects.create_user(
            username='head_finance_user', password='password', role=User.CAPO_ECONOMO, company=self.company1
        )
        self.head_maintainer_user = User.objects.create_user(
            username='head_maintainer_user', password='password', role=User.HEAD_MAINTAINER, company=self.company1
        )
        self.maintenance_manager_user = User.objects.create_user(
            username='maint_manager', password='password', role=User.MAINTENANCE_MANAGER, resort=self.resort1
        )

    def test_corporate_user_sees_only_their_company_reviews(self):
        self.client.login(username='corporate_user', password='password')
        response = self.client.get(reverse('reviews:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_reviews'], 1)

    def test_hr_user_sees_only_their_company_reviews(self):
        self.client.login(username='hr_user', password='password')
        response = self.client.get(reverse('reviews:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_reviews'], 1)

    def test_head_finance_user_sees_only_their_company_reviews(self):
        self.client.login(username='head_finance_user', password='password')
        response = self.client.get(reverse('reviews:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_reviews'], 1)

    def test_head_maintainer_user_sees_only_their_company_reviews(self):
        self.client.login(username='head_maintainer_user', password='password')
        response = self.client.get(reverse('reviews:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_reviews'], 1)

    def test_maintenance_manager_sees_only_their_resort_reviews(self):
        self.client.login(username='maint_manager', password='password')
        response = self.client.get(reverse('reviews:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_reviews'], 1)

class ScrapingURLManagementTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.company1 = Company.objects.create(name="Company A URLs")
        self.company2 = Company.objects.create(name="Company B URLs")
        self.owner1 = User.objects.create_user(username='owner1_urls', password='password', role=User.OWNER, company=self.company1)
        self.resort1 = Resort.objects.create(name="Resort A URLs", company=self.company1)
        self.resort2 = Resort.objects.create(name="Resort B URLs", company=self.company2)
        self.source = ReviewSource.objects.create(name="Test Source URLs")
        self.scraping_url = ScrapingURL.objects.create(resort=self.resort1, source=self.source, url="https://example.com/resort_a_urls")
        self.client.login(username='owner1_urls', password='password')

    def test_owner_can_access_manage_urls_page(self):
        response = self.client.get(reverse('reviews:manage_scraping_urls', args=[self.resort1.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Gestione URL di Scraping")

    def test_owner_cannot_access_other_company_urls_page(self):
        response = self.client.get(reverse('reviews:manage_scraping_urls', args=[self.resort2.pk]))
        self.assertRedirects(response, reverse('core:resort_list'))

    def test_owner_can_add_scraping_url(self):
        new_source = ReviewSource.objects.create(name="New Source")
        response = self.client.post(reverse('reviews:manage_scraping_urls', args=[self.resort1.pk]), {
            'source': new_source.pk,
            'url': 'https://new.example.com'
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(ScrapingURL.objects.filter(resort=self.resort1, source=new_source).exists())

    def test_owner_can_delete_scraping_url(self):
        response = self.client.post(reverse('reviews:delete_scraping_url', args=[self.scraping_url.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(ScrapingURL.objects.filter(pk=self.scraping_url.pk).exists())


class NewRolesReviewAccessTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.company1 = Company.objects.create(name="Company C")
        self.company2 = Company.objects.create(name="Company D")
        self.resort1 = Resort.objects.create(name="Resort C", company=self.company1)
        self.resort2 = Resort.objects.create(name="Resort D", company=self.company2)
        self.source = ReviewSource.objects.create(name="Test Source New Roles", scraper_identifier="test/scraper_new_roles")

        self.review_c = Review.objects.create(resort=self.resort1, source=self.source, rating=5, title="Stay C", review_date=timezone.now(), review_id="new_role_1")
        self.review_d = Review.objects.create(resort=self.resort2, source=self.source, rating=1, title="Stay D", review_date=timezone.now(), review_id="new_role_2")

        self.corporate_user = User.objects.create_user(
            username='corporate_user', password='password', role=User.CORPORATE, company=self.company1, has_reviews_access=True
        )
        self.hr_user = User.objects.create_user(
            username='hr_user', password='password', role=User.RISORSE_UMANE, company=self.company1, has_reviews_access=True
        )
        self.head_finance_user = User.objects.create_user(
            username='head_finance_user', password='password', role=User.CAPO_ECONOMO, company=self.company1, has_reviews_access=True
        )
        self.head_maintainer_user = User.objects.create_user(
            username='head_maintainer_user', password='password', role=User.HEAD_MAINTAINER, company=self.company1, has_reviews_access=True
        )

    def test_corporate_user_sees_only_their_company_reviews(self):
        self.client.login(username='corporate_user', password='password')
        response = self.client.get(reverse('reviews:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_reviews'], 1)
        self.assertContains(response, "Stay C")
        self.assertNotContains(response, "Stay D")

    def test_hr_user_sees_only_their_company_reviews(self):
        self.client.login(username='hr_user', password='password')
        response = self.client.get(reverse('reviews:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_reviews'], 1)
        self.assertContains(response, "Stay C")
        self.assertNotContains(response, "Stay D")

    def test_head_finance_user_sees_only_their_company_reviews(self):
        self.client.login(username='head_finance_user', password='password')
        response = self.client.get(reverse('reviews:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_reviews'], 1)
        self.assertContains(response, "Stay C")
        self.assertNotContains(response, "Stay D")

    def test_head_maintainer_user_sees_only_their_company_reviews(self):
        self.client.login(username='head_maintainer_user', password='password')
        response = self.client.get(reverse('reviews:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_reviews'], 1)
        self.assertContains(response, "Stay C")
        self.assertNotContains(response, "Stay D")

class VeratourIntegrationTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.company = Company.objects.create(name="Veratour Co")
        self.resort = Resort.objects.create(name="Veratour Resort", company=self.company)
        self.user = User.objects.create_superuser(username='admin_vera', password='password')
        self.client.login(username='admin_vera', password='password')

    def test_veratour_upload_wizard_access(self):
        response = self.client.get(reverse('reviews:veratour_upload'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Integrazione Veratour")

    def test_veratour_source_creation(self):
        from .veratour_utils import process_vota_commenti
        import os
        import pandas as pd

        # Create a mock Excel file
        df = pd.DataFrame({'Testo': ['01/01/2026 - Ottima vacanza', '02/01/2026 - Pessimo servizio']})
        file_path = 'test_vota.xlsx'
        df.to_excel(file_path, index=False)

        try:
            process_vota_commenti(file_path, self.resort)
            source = ReviewSource.objects.filter(name='Veratour').first()
            self.assertIsNotNone(source)
            self.assertEqual(Review.objects.filter(source=source).count(), 2)
        finally:
            if os.path.exists(file_path):
                os.remove(file_path)

    def test_cross_analysis_api(self):
        from .models import VeratourReport, ReviewAnalysis

        # 1. Create a Veratour Report with dummy data
        report_data = {
            "RISTORAZIONE": {"positive": 95, "negative": 5, "sub_items": {}},
            "GENERAL": {"positive": 98, "negative": 2, "sub_items": {}}
        }
        VeratourReport.objects.create(
            resort=self.resort,
            total_guests=100,
            max_capacity=1000,
            start_date=timezone.now().date(),
            end_date=timezone.now().date(),
            data=report_data
        )

        # 2. Create reviews mapped to RISTORAZIONE
        source, _ = ReviewSource.objects.get_or_create(name='Veratour')
        r1 = Review.objects.create(
            resort=self.resort, source=source, rating=2, text="Cibo pessimo",
            review_date=timezone.now(), review_id="vera_test_1"
        )
        ReviewAnalysis.objects.update_or_create(
            review=r1, defaults={'sentiment_score': -0.8, 'sentiment_label': 'negative', 'keywords': ['RISTORAZIONE']}
        )

        r2 = Review.objects.create(
            resort=self.resort, source=source, rating=10, text="Ottimo buffet",
            review_date=timezone.now(), review_id="vera_test_2"
        )
        ReviewAnalysis.objects.update_or_create(
            review=r2, defaults={'sentiment_score': 0.9, 'sentiment_label': 'positive', 'keywords': ['RISTORAZIONE']}
        )

        # 3. Call KPI Summary API
        url = reverse('reviews_api:kpi_summary_data')
        response = self.client.get(url, {'resorts': str(self.resort.id), 'include_internal': 'true'})

        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Verify cross-analysis presence
        veratour_data = data['overall']['veratour']
        self.assertIn('cross_analysis', veratour_data)

        # Find Ristorazione in cross-analysis
        risto = next(item for item in veratour_data['cross_analysis'] if item['department'] == 'RISTORAZIONE')
        self.assertEqual(risto['report_pos'], 95.0)
        # 50% pos (1 out of 2), 50% neg (1 out of 2)
        self.assertEqual(risto['ia_pos'], 50.0)
        self.assertEqual(risto['ia_neg'], 50.0)
        # Gap = IA Neg (50) - Report Neg (5) = 45
        self.assertEqual(risto['gap'], 45.0)
        self.assertTrue(risto['critical'])

        # Verify Alert
        self.assertIsNotNone(veratour_data['critical_alert'])
        self.assertEqual(veratour_data['critical_alert']['title'], 'Discrepanza Rilevata')
