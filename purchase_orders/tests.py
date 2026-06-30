from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from decimal import Decimal

from .models import Supplier, PurchaseOrder, PurchaseOrderItem, Budget
from resort.models import Resort
from clients.models import Company

User = get_user_model()

class PurchaseOrderTestCase(TestCase):
    """
    Test case for the Purchase Order system.
    Sets up a comprehensive environment with different user roles and objects.
    """
    @classmethod
    def setUpTestData(cls):
        # Create Company
        cls.company1 = Company.objects.create(name="Test Company 1")
        cls.company2 = Company.objects.create(name="Test Company 2")

        # Create Resorts
        cls.resort1 = Resort.objects.create(name="Resort A", company=cls.company1)
        cls.resort2 = Resort.objects.create(name="Resort B", company=cls.company1)
        cls.resort3 = Resort.objects.create(name="Resort C", company=cls.company2)

        # Create Users
        # Note: create_superuser only sets is_staff and is_superuser. We must set the role manually.
        cls.superadmin = User.objects.create_superuser("superadmin", "super@test.com", "password", role=User.SUPERADMIN)
        cls.superadmin.can_manage_purchase_orders = True
        cls.superadmin.save()

        cls.owner = User.objects.create_user("owner", "owner@test.com", "password", role=User.OWNER, company=cls.company1, can_manage_purchase_orders=True)
        cls.director1 = User.objects.create_user("director1", "dir1@test.com", "password", role=User.DIRECTOR, resort=cls.resort1, company=cls.company1, can_manage_purchase_orders=True)
        cls.director2 = User.objects.create_user("director2", "dir2@test.com", "password", role=User.DIRECTOR, resort=cls.resort2, can_manage_purchase_orders=True)
        cls.staff1 = User.objects.create_user("staff1", "staff1@test.com", "password", role=User.MAINTAINER, resort=cls.resort1, can_manage_purchase_orders=True)
        cls.unauthorized_user = User.objects.create_user("unauthorized", "unauth@test.com", "password", role=User.RECEPTIONIST, can_manage_purchase_orders=False)

        # Create Suppliers
        cls.supplier1 = Supplier.objects.create(name="Supplier X", company=cls.company1)
        cls.supplier2 = Supplier.objects.create(name="Supplier Y", company=cls.company1)
        cls.supplier3 = Supplier.objects.create(name="Supplier Z", company=cls.company2)

        # Create Purchase Orders
        cls.po1 = PurchaseOrder.objects.create(resort=cls.resort1, supplier=cls.supplier1, created_by=cls.staff1)
        cls.po2 = PurchaseOrder.objects.create(resort=cls.resort2, supplier=cls.supplier2, created_by=cls.director2)
        cls.po3 = PurchaseOrder.objects.create(resort=cls.resort3, supplier=cls.supplier1, created_by=cls.superadmin) # Belongs to company2

        # Create Purchase Order Items
        PurchaseOrderItem.objects.create(purchase_order=cls.po1, product_name="Laptop", quantity=2, unit_price=Decimal("1200.00"))
        PurchaseOrderItem.objects.create(purchase_order=cls.po1, product_name="Mouse", quantity=2, unit_price=Decimal("25.00"))
        PurchaseOrderItem.objects.create(purchase_order=cls.po2, product_name="Shampoo", quantity=100, unit_price=Decimal("5.50"))

        # Create Budget
        cls.budget1 = Budget.objects.create(resort=cls.resort1, year=2025, month=8, amount=Decimal("10000.00"))

    def test_model_properties(self):
        """Test the calculated properties on the models."""
        self.assertEqual(self.po1.total_amount, Decimal("2450.00"))
        self.assertEqual(self.po2.total_amount, Decimal("550.00"))
        item = self.po1.items.first()
        self.assertEqual(item.total_price, Decimal("2400.00"))

    def test_access_decorator_permissions(self):
        """Test the purchase_order_access_required decorator denies access to unauthorized users."""
        # Test that a user without the permission flag gets redirected
        self.client.login(username="unauthorized", password="password")
        response = self.client.get(reverse('purchase_orders:list'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('home'))

        # Test that a user with the permission flag gets access
        self.client.login(username="staff1", password="password")
        response = self.client.get(reverse('purchase_orders:list'))
        self.assertEqual(response.status_code, 200)

    def test_list_view_permissions(self):
        """Test that each user role sees the correct list of purchase orders."""
        # Superadmin sees all
        self.client.login(username="superadmin", password="password")
        response = self.client.get(reverse('purchase_orders:list'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['purchase_orders']), 3)

        # Owner sees all orders from their company (company1)
        self.client.login(username="owner", password="password")
        response = self.client.get(reverse('purchase_orders:list'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['purchase_orders']), 2)
        self.assertNotIn(self.po3, response.context['purchase_orders'])

        # Director1 sees all orders from their resort (resort1)
        self.client.login(username="director1", password="password")
        response = self.client.get(reverse('purchase_orders:list'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['purchase_orders']), 1)
        self.assertEqual(response.context['purchase_orders'][0], self.po1)

        # Staff1 only sees orders they created
        self.client.login(username="staff1", password="password")
        response = self.client.get(reverse('purchase_orders:list'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['purchase_orders']), 1)
        self.assertEqual(response.context['purchase_orders'][0], self.po1)

    def test_detail_view_permissions(self):
        """Test that users can only see details of orders they are allowed to see."""
        # Director1 should see po1 but not po2
        self.client.login(username="director1", password="password")
        response = self.client.get(reverse('purchase_orders:detail', kwargs={'pk': self.po1.pk}))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse('purchase_orders:detail', kwargs={'pk': self.po2.pk}))
        self.assertEqual(response.status_code, 404) # Access denied should result in 404

    def test_create_view(self):
        """Test the creation of a new purchase order."""
        self.client.login(username="director1", password="password")
        response = self.client.get(reverse('purchase_orders:create'))
        self.assertEqual(response.status_code, 200)

        post_data = {
            'resort': self.resort1.pk,
            'supplier': self.supplier1.pk,
        }
        response = self.client.post(reverse('purchase_orders:create'), data=post_data)
        self.assertEqual(response.status_code, 302) # Should redirect on success
        self.assertTrue(PurchaseOrder.objects.filter(created_by=self.director1, resort=self.resort1).exists())
        new_po = PurchaseOrder.objects.get(created_by=self.director1, resort=self.resort1)
        self.assertEqual(new_po.created_by, self.director1)

    def test_budget_access_permissions(self):
        """Test that only authorized roles can access budget views."""
        self.client.login(username="staff1", password="password")
        response = self.client.get(reverse('purchase_orders:budget_list'))
        self.assertEqual(response.status_code, 302) # Staff should be redirected
        self.assertRedirects(response, reverse('home'))

        self.client.login(username="director1", password="password")
        response = self.client.get(reverse('purchase_orders:budget_list'))
        self.assertEqual(response.status_code, 200) # Director should be allowed

    def test_create_form_content_for_owner(self):
        """
        Verify that the PO create form only shows suppliers and resorts
        from the logged-in owner's company.
        """
        self.client.login(username="owner", password="password")
        response = self.client.get(reverse('purchase_orders:create'))
        self.assertEqual(response.status_code, 200)

        # The owner belongs to company1
        # The form should contain suppliers and resorts from company1 only
        form = response.context['form']

        # Check suppliers
        suppliers_in_form = form.fields['supplier'].queryset
        self.assertIn(self.supplier1, suppliers_in_form)
        self.assertIn(self.supplier2, suppliers_in_form)
        self.assertNotIn(self.supplier3, suppliers_in_form)

        # Check resorts
        resorts_in_form = form.fields['resort'].queryset
        self.assertIn(self.resort1, resorts_in_form)
        self.assertIn(self.resort2, resorts_in_form)
        self.assertNotIn(self.resort3, resorts_in_form)

    def test_supplier_list_view(self):
        """Test the supplier list view."""
        self.client.login(username="director1", password="password")
        response = self.client.get(reverse('purchase_orders:supplier_list'))
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.supplier1, response.context['suppliers'])
        self.assertIn(self.supplier2, response.context['suppliers'])

    def test_pdf_export_view(self):
        """Test the PDF export view."""
        self.client.login(username="director1", password="password")
        response = self.client.get(reverse('purchase_orders:export_pdf', kwargs={'pk': self.po1.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertIn('attachment; filename="ordine_1.pdf"', response['Content-Disposition'])

    def test_excel_export_view(self):
        """Test the Excel export view."""
        self.client.login(username="owner", password="password")
        response = self.client.get(reverse('purchase_orders:export_excel'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

    def test_update_view_with_formset(self):
        """Test updating a PO with items using the formset."""
        self.client.login(username="director1", password="password")

        # Data for the main form and the formset
        po_data = {
            'resort': self.po1.resort.pk,
            'supplier': self.po1.supplier.pk,
            'status': 'submitted',
        }

        # Formset data: update one item, delete another, add a new one
        item_data = {
            'items-TOTAL_FORMS': '3',
            'items-INITIAL_FORMS': '2',
            'items-MIN_NUM_FORMS': '0',
            'items-MAX_NUM_FORMS': '1000',
            # Update first item
            'items-0-id': self.po1.items.all()[0].pk,
            'items-0-product_name': 'Laptop Pro',
            'items-0-product_code': 'LP123',
            'items-0-quantity': '3',
            'items-0-unit_price': '1300.00',
            # Delete second item
            'items-1-id': self.po1.items.all()[1].pk,
            'items-1-DELETE': 'on',
            # Add new item
            'items-2-product_name': 'Keyboard',
            'items-2-product_code': 'KB01',
            'items-2-quantity': '5',
            'items-2-unit_price': '75.00',
        }

        post_data = {**po_data, **item_data}

        response = self.client.post(reverse('purchase_orders:update', kwargs={'pk': self.po1.pk}), data=post_data)
        self.assertEqual(response.status_code, 302) # Should redirect to detail view

        # Verify the changes
        self.po1.refresh_from_db()
        self.assertEqual(self.po1.status, 'submitted')
        self.assertEqual(self.po1.items.count(), 2) # 1 updated, 1 deleted, 1 added

        # Check updated item
        updated_item = self.po1.items.get(product_name="Laptop Pro")
        self.assertEqual(updated_item.quantity, 3)

        # Check added item
        self.assertTrue(self.po1.items.filter(product_name="Keyboard").exists())

        # Check total amount
        expected_total = (3 * 1300) + (5 * 75) # (3*1300) + (5*75) = 3900 + 375 = 4275
        self.assertEqual(self.po1.total_amount, Decimal("4275.00"))
