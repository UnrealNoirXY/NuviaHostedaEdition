from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from .models import Company

User = get_user_model()

class CompanyManagementTest(TestCase):
    def setUp(self):
        # Create a superuser
        self.superuser = User.objects.create_superuser(
            username='superuser',
            password='password123',
            email='super@user.com'
        )
        # Create a regular user
        self.user = User.objects.create_user(
            username='testuser',
            password='password123',
            role='director'
        )

    def test_superuser_can_access_company_list(self):
        """
        Test that a superuser can access the company list page.
        """
        self.client.login(username='superuser', password='password123')
        response = self.client.get(reverse('clients:company_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'clients/company_list.html')

    def test_regular_user_cannot_access_company_list(self):
        """
        Test that a non-superuser is redirected from the company list page.
        """
        self.client.login(username='testuser', password='password123')
        response = self.client.get(reverse('clients:company_list'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('home'))

    def test_superuser_can_create_company(self):
        """
        Test that a superuser can create a new company.
        """
        self.client.login(username='superuser', password='password123')
        response = self.client.post(reverse('clients:company_create'), {
            'name': 'New Test Company',
            'is_active': True
        })
        self.assertEqual(response.status_code, 302) # Should redirect after successful creation
        self.assertTrue(Company.objects.filter(name='New Test Company').exists())

    def test_company_str_representation(self):
        """
        Test the __str__ method of the Company model.
        """
        company = Company.objects.create(name='My Test Company')
        self.assertEqual(str(company), 'My Test Company')
