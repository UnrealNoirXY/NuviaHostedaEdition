from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from clients.models import Company
from resort.models import Resort

from . import models


class EconomatoOverviewTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name='Vision Hospitality Group')
        self.other_company = Company.objects.create(name='Aurora Holdings')
        self.resort_a = Resort.objects.create(company=self.company, name='Luna Bay Resort')
        self.resort_b = Resort.objects.create(company=self.company, name='Stellar Suites')
        self.resort_other = Resort.objects.create(company=self.other_company, name='Nebula Retreat')

        self.superuser = User.objects.create_superuser('root', 'root@example.com', 'password123')
        self.director = User.objects.create_user(
            username='director',
            password='password123',
            role=User.DIRECTOR,
            company=self.company,
            resort=self.resort_a,
        )

        self.item_resort_a = models.EconomatoItem.objects.create(
            company=self.company,
            resort=self.resort_a,
            code='A-001',
            name='Set Cortesia Deluxe',
            reorder_point=5,
            optimal_stock=20,
        )
        self.item_resort_b = models.EconomatoItem.objects.create(
            company=self.company,
            resort=self.resort_b,
            code='A-002',
            name='Linea Wellness',
            reorder_point=3,
            optimal_stock=15,
        )
        self.item_other_company = models.EconomatoItem.objects.create(
            company=self.other_company,
            resort=self.resort_other,
            code='B-001',
            name='Amenities Cosmici',
            reorder_point=2,
            optimal_stock=8,
        )

        models.EconomatoStockLevel.objects.create(
            item=self.item_resort_a,
            resort=self.resort_a,
            quantity=4,
            reserved_quantity=0,
        )
        models.EconomatoStockLevel.objects.create(
            item=self.item_resort_b,
            resort=self.resort_b,
            quantity=10,
            reserved_quantity=0,
        )

        request_a = models.EconomatoRequest.objects.create(
            company=self.company,
            resort=self.resort_a,
            status=models.EconomatoRequest.STATUS_PENDING,
            priority=models.EconomatoRequest.PRIORITY_HIGH,
            total_estimated_cost=250,
            created_at=timezone.now(),
        )
        models.EconomatoRequestItem.objects.create(
            request=request_a,
            description='Set cortesia camere deluxe',
            quantity=10,
            unit_cost=10,
        )
        request_b = models.EconomatoRequest.objects.create(
            company=self.company,
            resort=self.resort_b,
            status=models.EconomatoRequest.STATUS_APPROVED,
            priority=models.EconomatoRequest.PRIORITY_MEDIUM,
            total_estimated_cost=120,
            created_at=timezone.now(),
        )
        models.EconomatoRequestItem.objects.create(
            request=request_b,
            description='Linea wellness spa',
            quantity=6,
            unit_cost=20,
        )

        request_other = models.EconomatoRequest.objects.create(
            company=self.other_company,
            resort=self.resort_other,
            status=models.EconomatoRequest.STATUS_PENDING,
            priority=models.EconomatoRequest.PRIORITY_MEDIUM,
            total_estimated_cost=90,
            created_at=timezone.now(),
        )
        models.EconomatoRequestItem.objects.create(
            request=request_other,
            description='Amenities interstellari',
            quantity=3,
            unit_cost=30,
        )

    def test_superuser_can_select_company_and_resort(self):
        self.client.force_login(self.superuser)
        url = reverse('economato:overview') + f'?company={self.company.id}&resort={self.resort_b.id}'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['scope']['current_company_id'], self.company.id)
        self.assertEqual(data['scope']['current_resort_id'], self.resort_b.id)
        self.assertEqual(data['stats']['total_items'], 1.0)
        self.assertIn('Stellar Suites', [req['resort_name'] for req in data['recent_requests']])

    def test_director_only_sees_own_resort(self):
        self.client.force_login(self.director)
        response = self.client.get(reverse('economato:overview'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        # Director sees only items and requests of their resort
        self.assertEqual(data['stats']['total_items'], 1.0)
        self.assertEqual(data['scope']['current_resort_id'], self.resort_a.id)
        self.assertTrue(all(req['resort'] == self.resort_a.id for req in data['recent_requests']))
        # Ensure other company data is excluded
        self.assertNotIn(self.item_other_company.id, [item['item'] for item in data['low_stock_items']])
