from django.test import TestCase
from django.urls import reverse
from accounts.models import User
from .models import Asset, AssetCategory

from resort.models import Resort

class AssetCRUDTestCase(TestCase):
    def setUp(self):
        # Create a superuser to bypass permission checks in views
        self.user = User.objects.create_superuser(username='assetadmin', password='password123', email='asset@test.com')
        self.client.login(username='assetadmin', password='password123')

        self.resort = Resort.objects.create(name='Test Resort')
        self.category = AssetCategory.objects.create(name='Laptop')

        self.asset = Asset.objects.create(
            name='Developer Laptop 01',
            category=self.category,
            resort=self.resort,
            serial_number='DEV-LP-001'
        )

    def test_asset_list_view(self):
        """ Tests that the asset list view loads and contains the created asset. """
        response = self.client.get(reverse('assets:asset-list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.asset.name)
        self.assertTemplateUsed(response, 'assets/asset_list.html')

    def test_asset_detail_view(self):
        """ Tests that the asset detail view loads correctly. """
        response = self.client.get(reverse('assets:asset-detail', kwargs={'pk': self.asset.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.asset.serial_number)
        self.assertTemplateUsed(response, 'assets/asset_detail.html')

    def test_asset_create_view(self):
        """ Tests that a new asset can be created. """
        url = reverse('assets:asset-create')
        data = {
            'name': 'New Test Asset',
            'category': self.category.pk,
            'resort': self.resort.pk,
            'serial_number': 'TEST-001',
            'purchase_cost': '1200.50',
        }
        response = self.client.post(url, data)
        self.assertRedirects(response, reverse('assets:asset-list'))
        self.assertTrue(Asset.objects.filter(name='New Test Asset').exists())

    def test_asset_update_view(self):
        """ Tests that an existing asset can be updated. """
        url = reverse('assets:asset-update', kwargs={'pk': self.asset.pk})
        updated_name = 'Updated Laptop Name'
        data = {
            'name': updated_name,
            'category': self.category.pk,
            'resort': self.resort.pk,
            'serial_number': self.asset.serial_number,
            'purchase_cost': '1300.00',
        }
        response = self.client.post(url, data)
        self.assertRedirects(response, reverse('assets:asset-list'))

        self.asset.refresh_from_db()
        self.assertEqual(self.asset.name, updated_name)

    def test_asset_delete_view(self):
        """ Tests that an asset can be deleted. """
        url = reverse('assets:asset-delete', kwargs={'pk': self.asset.pk})
        response = self.client.post(url)
        self.assertRedirects(response, reverse('assets:asset-list'))
        self.assertFalse(Asset.objects.filter(pk=self.asset.pk).exists())
