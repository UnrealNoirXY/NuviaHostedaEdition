from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from decimal import Decimal

from .models import InventoryItem, StockRecord
from purchase_orders.models import Supplier, PurchaseOrder, PurchaseOrderItem
from resort.models import Resort
from clients.models import Company

User = get_user_model()

class InventoryTestCase(TestCase):
    """
    Test case for the Inventory system, focusing on integration with Purchase Orders.
    """
    @classmethod
    def setUpTestData(cls):
        # Create Company and Resort
        cls.company = Company.objects.create(name="Test Inventory Co")
        cls.resort = Resort.objects.create(name="Resort Inventory", company=cls.company)

        # Create Users
        cls.director = User.objects.create_user("inv_director", "inv_dir@test.com", "password", role=User.DIRECTOR, resort=cls.resort, company=cls.company, has_inventory_access=True)
        cls.unauthorized_user = User.objects.create_user("inv_unauthorized", "inv_unauth@test.com", "password", role=User.RECEPTIONIST, has_inventory_access=False)

        # Create Supplier and a base Inventory Item
        cls.supplier = Supplier.objects.create(name="Inventory Supplier")
        cls.item1 = InventoryItem.objects.create(resort=cls.resort, name="Shampoo", product_code="SHMP01", current_stock=10)

    def test_signal_on_po_completion(self):
        """
        Tests that the inventory is updated correctly when a PO is marked as 'completed'.
        """
        # Create a new Purchase Order
        po = PurchaseOrder.objects.create(
            resort=self.resort,
            supplier=self.supplier,
            created_by=self.director,
            status='draft'
        )
        # Add an item that already exists in inventory
        PurchaseOrderItem.objects.create(
            purchase_order=po,
            product_name="Shampoo",
            product_code="SHMP01",
            quantity=50,
            unit_price=Decimal("5.00")
        )
        # Add a new item that doesn't exist yet
        PurchaseOrderItem.objects.create(
            purchase_order=po,
            product_name="Soap",
            product_code="SOAP01",
            quantity=100,
            unit_price=Decimal("2.00")
        )

        # Mark the PO as completed and save
        po.status = 'completed'
        po.save()

        # Check the existing inventory item
        self.item1.refresh_from_db()
        self.assertEqual(self.item1.current_stock, 60) # 10 initial + 50 from PO

        # Check the new inventory item
        new_item = InventoryItem.objects.get(product_code="SOAP01", resort=self.resort)
        self.assertIsNotNone(new_item)
        self.assertEqual(new_item.current_stock, 100)
        self.assertEqual(new_item.name, "Soap")

        # Check that StockRecords were created
        self.assertEqual(StockRecord.objects.count(), 2)
        shampoo_record = StockRecord.objects.get(item=self.item1)
        self.assertEqual(shampoo_record.change, 50)
        self.assertEqual(shampoo_record.reason, 'purchase')
        self.assertEqual(shampoo_record.purchase_order, po)

        # Test idempotency: saving the PO again as 'completed' should not trigger the signal again
        po.save()
        self.item1.refresh_from_db()
        self.assertEqual(self.item1.current_stock, 60) # Should still be 60
        self.assertEqual(StockRecord.objects.count(), 2) # Should still be 2 records

    def test_inventory_view_permissions(self):
        """
        Tests that only authorized users can access the inventory views.
        """
        # Unauthorized user should be redirected
        self.client.login(username="inv_unauthorized", password="password")
        response = self.client.get(reverse('inventory:list'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('home'))

        # Authorized user should be allowed
        self.client.login(username="inv_director", password="password")
        response = self.client.get(reverse('inventory:list'))
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.item1, response.context['items'])

    def test_stock_adjustment_view(self):
        """Tests the stock adjustment view for making manual changes."""
        self.client.login(username="inv_director", password="password")
        initial_stock = self.item1.current_stock

        # Test a withdrawal
        post_data = {
            'change': '-2',
            'reason': 'withdrawal',
            'notes': 'Used for cleaning room 101'
        }
        response = self.client.post(reverse('inventory:adjust_stock', kwargs={'item_pk': self.item1.pk}), data=post_data)
        self.assertEqual(response.status_code, 302) # Should redirect to detail view

        self.item1.refresh_from_db()
        self.assertEqual(self.item1.current_stock, initial_stock - 2)

        # Check that a stock record was created
        self.assertTrue(StockRecord.objects.filter(item=self.item1, change=-2, reason='withdrawal').exists())

    def test_inventory_item_creation_with_initial_stock(self):
        """Tests that creating an item with initial stock also creates a stock record."""
        self.client.login(username="inv_director", password="password")

        post_data = {
            'resort': self.resort.pk,
            'name': 'New Towels',
            'product_code': 'TWL01',
            'current_stock': '150'
        }
        response = self.client.post(reverse('inventory:create'), data=post_data)
        self.assertEqual(response.status_code, 302) # Redirects to list view

        # Check the new item
        new_item = InventoryItem.objects.get(product_code='TWL01')
        self.assertEqual(new_item.current_stock, 150)

        # Check that the initial stock record was created
        self.assertTrue(StockRecord.objects.filter(item=new_item, change=150, reason='initial').exists())
