from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
import importlib
from django.core.files.uploadedfile import SimpleUploadedFile
from clients.models import Company
from .models import Procedure, Sector

User = get_user_model()

class ProcedureSegregationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Create Companies
        cls.company1 = Company.objects.create(name="Company A")
        cls.company2 = Company.objects.create(name="Company B")

        # Create Users
        cls.superadmin = User.objects.create_superuser("superadmin", "super@test.com", "password", role='superadmin')
        cls.owner1 = User.objects.create_user("owner1", "owner1@test.com", "password", role='owner', company=cls.company1)
        cls.owner2 = User.objects.create_user("owner2", "owner2@test.com", "password", role='owner', company=cls.company2)
        cls.staff1 = User.objects.create_user("staff1", "staff1@test.com", "password", role='maintainer', company=cls.company1)

        # Get the Sector created by the migration
        cls.maintenance_sector = Sector.objects.get(role_key="maintainer")

        # Create a dummy file for upload
        cls.dummy_file = SimpleUploadedFile("test_procedure.pdf", b"file_content", content_type="application/pdf")

        # Create Procedures
        cls.proc1_company1 = Procedure.objects.create(
            title="Procedure 1 - Company A",
            company=cls.company1,
            uploaded_by=cls.owner1,
            file=cls.dummy_file
        )
        cls.proc2_company1 = Procedure.objects.create(
            title="Procedure 2 - Company A",
            company=cls.company1,
            uploaded_by=cls.owner1,
            file=cls.dummy_file
        )
        cls.proc2_company1.sectors.add(cls.maintenance_sector)

        cls.proc1_company2 = Procedure.objects.create(
            title="Procedure 1 - Company B",
            company=cls.company2,
            uploaded_by=cls.owner2,
            file=cls.dummy_file
        )

    def test_list_view_for_superadmin(self):
        self.client.login(username="superadmin", password="password")
        response = self.client.get(reverse('procedures:procedure_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.proc1_company1.title)
        self.assertContains(response, self.proc1_company2.title)
        self.assertEqual(len(response.context['procedures']), 3)

    def test_list_view_for_owner1(self):
        self.client.login(username="owner1", password="password")
        response = self.client.get(reverse('procedures:procedure_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.proc1_company1.title)
        self.assertNotContains(response, self.proc1_company2.title)
        self.assertEqual(len(response.context['procedures']), 2)

    def test_list_view_for_owner2(self):
        self.client.login(username="owner2", password="password")
        response = self.client.get(reverse('procedures:procedure_list'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, self.proc1_company1.title)
        self.assertContains(response, self.proc1_company2.title)
        self.assertEqual(len(response.context['procedures']), 1)

    def test_list_view_for_staff(self):
        self.client.login(username="staff1", password="password")
        response = self.client.get(reverse('procedures:procedure_list'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, self.proc1_company1.title) # Not in staff's sector
        self.assertContains(response, self.proc2_company1.title) # In staff's sector
        self.assertNotContains(response, self.proc1_company2.title) # Different company
        self.assertEqual(len(response.context['procedures']), 1)

    def test_owner1_cannot_access_company2_procedure_detail(self):
        self.client.login(username="owner1", password="password")
        response = self.client.get(reverse('procedures:procedure_viewer', kwargs={'pk': self.proc1_company2.pk}))
        self.assertEqual(response.status_code, 404)

    def test_owner_can_update_own_company_procedure(self):
        self.client.login(username="owner1", password="password")
        response = self.client.get(reverse('procedures:procedure_update', kwargs={'pk': self.proc1_company1.pk}))
        self.assertEqual(response.status_code, 200)

    def test_owner_cannot_update_other_company_procedure(self):
        self.client.login(username="owner1", password="password")
        response = self.client.get(reverse('procedures:procedure_update', kwargs={'pk': self.proc1_company2.pk}))
        self.assertEqual(response.status_code, 404)

    def test_owner_can_delete_own_company_procedure(self):
        self.client.login(username="owner1", password="password")
        response = self.client.get(reverse('procedures:procedure_delete', kwargs={'pk': self.proc1_company1.pk}))
        self.assertEqual(response.status_code, 200)

    def test_owner_cannot_delete_other_company_procedure(self):
        self.client.login(username="owner1", password="password")
        response = self.client.get(reverse('procedures:procedure_delete', kwargs={'pk': self.proc1_company2.pk}))
        self.assertEqual(response.status_code, 404)

    def test_template_content_for_superadmin(self):
        """Superadmin should see Company column and edit/delete buttons."""
        self.client.login(username="superadmin", password="password")
        response = self.client.get(reverse('procedures:procedure_list'))
        self.assertContains(response, '<th>Azienda</th>', html=True)
        self.assertContains(response, 'btn-warning', msg_prefix="Edit button not found for superadmin")
        self.assertContains(response, 'btn-danger', msg_prefix="Delete button not found for superadmin")

    def test_template_content_for_owner(self):
        """Owner should see edit/delete buttons but NOT the Company column."""
        self.client.login(username="owner1", password="password")
        response = self.client.get(reverse('procedures:procedure_list'))
        self.assertNotContains(response, '<th>Azienda</th>', html=True)
        self.assertContains(response, 'btn-warning', msg_prefix="Edit button not found for owner")
        self.assertContains(response, 'btn-danger', msg_prefix="Delete button not found for owner")

    def test_procedure_upload_assigns_correct_company(self):
        self.client.login(username="owner1", password="password")

        # Create a new dummy file for this test to avoid issues with closed files
        dummy_file = SimpleUploadedFile("new_procedure.pdf", b"content", "application/pdf")

        post_data = {
            'title': 'New Test Procedure',
            'file': dummy_file,
            'sectors': [self.maintenance_sector.pk]
        }
        response = self.client.post(reverse('procedures:procedure_upload'), data=post_data)

        self.assertEqual(response.status_code, 302)
        self.assertTrue(Procedure.objects.filter(title='New Test Procedure').exists())
        new_procedure = Procedure.objects.get(title='New Test Procedure')
        self.assertEqual(new_procedure.company, self.owner1.company)

    # def test_data_migration_handles_orphan_procedures(self):
    #     """
    #     Tests that the data migration correctly assigns a default company
    #     to procedures that have no uploader or an uploader without a company.
    #     """
    #     # 1. Create a user with NO company
    #     user_no_company = User.objects.create_user("nocorp", "nocorp@test.com", "password", role='maintainer')

    #     # 2. Create orphan procedures with company=None to simulate pre-migration state
    #     orphan_proc_1 = Procedure.objects.create(
    #         title="Orphan Procedure 1",
    #         uploaded_by=None,
    #         file=self.dummy_file,
    #         company=None
    #     )
    #     orphan_proc_2 = Procedure.objects.create(
    #         title="Orphan Procedure 2",
    #         uploaded_by=user_no_company,
    #         file=self.dummy_file,
    #         company=None
    #     )

    #     # 3. Get the migration function and run it
    #     class MockApps:
    #         def get_model(self, app_label, model_name):
    #             if app_label == 'procedures' and model_name == 'Procedure':
    #                 return Procedure
    #             if app_label == 'clients' and model_name == 'Company':
    #                 return Company
    #             raise LookupError()

    #     migration_module = importlib.import_module("procedures.migrations.0004_populate_procedure_company")
    #     populate_procedure_company = migration_module.populate_procedure_company
    #     populate_procedure_company(MockApps(), None)

    #     # 4. Verify that the orphan procedures have been assigned the default company
    #     orphan_proc_1.refresh_from_db()
    #     orphan_proc_2.refresh_from_db()

    #     default_company = Company.objects.order_by('pk').first()
    #     self.assertEqual(orphan_proc_1.company, default_company)
    #     self.assertEqual(orphan_proc_2.company, default_company)
