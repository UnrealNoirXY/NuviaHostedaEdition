from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from clients.models import Company
from resort.models import Resort

from .models import FinancialPeriod, FinancialSnapshot


class FinancialDashboardViewTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name='Azienda Test')
        self.resort = Resort.objects.create(name='Resort Test', company=self.company)
        self.user = User.objects.create_user(
            username='owner',
            password='password123',
            role=User.OWNER,
            company=self.company,
            resort=self.resort,
        )
        period = FinancialPeriod.objects.create(
            company=self.company,
            resort=self.resort,
            period_type=FinancialPeriod.PERIOD_MONTHLY,
            year=2024,
            month=1,
        )
        FinancialSnapshot.objects.create(
            period=period,
            snapshot_type=FinancialSnapshot.TYPE_ACTUAL,
            total_revenue=Decimal('1000.00'),
            total_costs=Decimal('400.00'),
        )
        FinancialSnapshot.objects.create(
            period=period,
            snapshot_type=FinancialSnapshot.TYPE_BUDGET,
            total_revenue=Decimal('900.00'),
            total_costs=Decimal('450.00'),
        )

    def test_dashboard_accessible_for_owner(self):
        self.client.login(username='owner', password='password123')
        response = self.client.get(reverse('financials:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('actual_totals', response.context)
        self.assertEqual(response.context['actual_totals']['revenue'], Decimal('1000.00'))
        self.assertEqual(response.context['revenue_attainment'].quantize(Decimal('0.01')), Decimal('111.11'))
        self.assertEqual(response.context['cost_efficiency'].quantize(Decimal('0.01')), Decimal('88.89'))
        self.assertEqual(response.context['margin_coverage'].quantize(Decimal('0.01')), Decimal('133.33'))
        self.assertIn('health_score', response.context)
        self.assertGreaterEqual(response.context['health_score'], Decimal('0'))
        self.assertIn('health_label', response.context)
        run_rate = response.context['run_rate_totals']
        self.assertIn('margin', run_rate)
        self.assertIn('months_recorded', run_rate)
        self.assertGreater(run_rate['factor'], Decimal('0'))
        self.assertIn('strategic_alerts', response.context)
        self.assertTrue(response.context['strategic_alerts'])
        self.assertIn('strategic_opportunities', response.context)
        self.assertIn('category_table', response.context)
        self.assertEqual(len(response.context['category_table']), 0)
        self.assertEqual(response.context['total_import_batches'], 0)
        self.assertContains(
            response,
            f"Cruscotto amministrativo {response.context['selected_year']}",
        )
        self.assertContains(response, 'Indice di Salute')
        self.assertContains(response, 'Alert Strategici')

    def test_dashboard_forbidden_for_receptionist(self):
        receptionist = User.objects.create_user(
            username='reception',
            password='password123',
            role=User.RECEPTIONIST,
            resort=self.resort,
        )
        self.client.login(username='reception', password='password123')
        response = self.client.get(reverse('financials:dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('home'))


class FinancialSnapshotListViewTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name='Azienda Due')
        self.resort = Resort.objects.create(name='Resort Due', company=self.company)
        self.user = User.objects.create_user(
            username='admin',
            password='password123',
            role=User.ADMINISTRATIVE,
            company=self.company,
            resort=self.resort,
        )
        period = FinancialPeriod.objects.create(
            company=self.company,
            resort=self.resort,
            period_type=FinancialPeriod.PERIOD_MONTHLY,
            year=2024,
            month=2,
        )
        FinancialSnapshot.objects.create(
            period=period,
            snapshot_type=FinancialSnapshot.TYPE_ACTUAL,
            total_revenue=Decimal('500.00'),
            total_costs=Decimal('300.00'),
        )

    def test_snapshot_list_view(self):
        self.client.login(username='admin', password='password123')
        response = self.client.get(reverse('financials:snapshot_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Snapshot Finanziari')
        snapshots = response.context['snapshots']
        self.assertEqual(snapshots.count(), 1)
        self.assertEqual(snapshots.first().total_revenue, Decimal('500.00'))
