from datetime import date

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.test import override_settings
from django.utils import timezone

from accounts.models import User
from clients.models import Company, Structure, StructureRole, StructureMembership
from .models import Allergene, Ingrediente, Piatto, Menu, MenuDocumentJob
from .tasks import cleanup_expired_documents_task


class MenuGeneratorAPITests(APITestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Test Company")
        self.structure = Structure.objects.create(
            name="Hotel Test",
            slug="hotel-test",
            company=self.company,
        )
        self.role_all, _ = StructureRole.objects.get_or_create(
            company=self.company,
            name="Executive Chef",
            defaults={
                "can_edit_menus": True,
                "can_edit_dishes": True,
                "can_manage_allergens": True,
                "can_publish_menu": True,
                "can_edit_layouts": True,
                "can_manage_templates": True,
                "can_approve_menu": True,
            },
        )

        self.superadmin = User.objects.create_superuser(
            username='superadmin',
            password='password123',
            company=self.company,
        )

        self.authorized_user = User.objects.create_user(
            username='authorized',
            password='password123',
            company=self.company,
            menu_creation_studio_enabled=True,
        )
        StructureMembership.objects.create(
            user=self.authorized_user,
            structure=self.structure,
            role=self.role_all,
            valid_from=date.today(),
        )

        self.unauthorized_user = User.objects.create_user(
            username='unauthorized',
            password='password123',
            company=self.company,
            menu_creation_studio_enabled=True,
        )

    def test_superadmin_can_access_api(self):
        self.client.login(username='superadmin', password='password123')
        url = reverse('menu_generator_api:piatto-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_authorized_user_can_access_api(self):
        self.client.login(username='authorized', password='password123')
        url = reverse('menu_generator_api:piatto-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_unauthorized_user_is_forbidden(self):
        self.client.login(username='unauthorized', password='password123')
        url = reverse('menu_generator_api:piatto-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_piatto_requires_permission(self):
        self.client.login(username='authorized', password='password123')
        url = reverse('menu_generator_api:piatto-list')
        data = {
            'nome': 'Spaghetti alla Carbonara',
            'categoria': 'primo',
            'porzioni': 1,
            'ingredienti_ids': [],
            'allergeni_ids': [],
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Piatto.objects.count(), 1)

    def test_create_piatto_without_permission_is_forbidden(self):
        limited_role = StructureRole.objects.create(
            company=self.company,
            name="Viewer",
            can_edit_dishes=False,
            can_manage_allergens=False,
        )
        limited_user = User.objects.create_user(
            username='viewer',
            password='password123',
            company=self.company,
            menu_creation_studio_enabled=True,
        )
        StructureMembership.objects.create(
            user=limited_user,
            structure=self.structure,
            role=limited_role,
            valid_from=date.today(),
        )

        self.client.login(username='viewer', password='password123')
        url = reverse('menu_generator_api:piatto-list')
        payload = {
            'nome': 'Pane e acqua',
            'categoria': 'altro',
            'porzioni': 1,
            'ingredienti_ids': [],
            'allergeni_ids': [],
        }
        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_piatto_filters_and_clone_variant(self):
        self.client.login(username='authorized', password='password123')
        pesce = Allergene.objects.create(codice="PES", nome="Pesce")
        latte = Allergene.objects.create(codice="LAT", nome="Latte")
        gambero = Ingrediente.objects.create(company=self.company, nome="Gambero")
        gambero.allergeni.add(pesce)
        latte_ing = Ingrediente.objects.create(company=self.company, nome="Latte fresco")
        latte_ing.allergeni.add(latte)

        estivo = Piatto.objects.create(
            nome="Risotto ai gamberi",
            categoria="primo",
            company=self.company,
            stagionalita="estate",
            descrizione="Con crostacei freschi",
            is_active=True,
        )
        estivo.allergeni.add(pesce)
        estivo.ingredienti.add(gambero)

        invernale = Piatto.objects.create(
            nome="Lasagna alla bolognese",
            categoria="primo",
            company=self.company,
            stagionalita="inverno",
            descrizione="Ricca di besciamella",
            is_active=False,
        )
        invernale.allergeni.add(latte)
        invernale.ingredienti.add(latte_ing)

        url = reverse('menu_generator_api:piatto-list')
        response = self.client.get(url, {
            'stagionalita': 'estate',
            'allergeni': pesce.id,
            'search': 'gambero',
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['nome'], "Risotto ai gamberi")

        response = self.client.get(url, {
            'exclude_allergeni': pesce.id,
            'include_inactive': True,
        })
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['nome'], "Lasagna alla bolognese")

        clone_url = reverse('menu_generator_api:piatto-clone', args=[estivo.id])
        clone_resp = self.client.post(clone_url, {'nome': 'Risotto ai gamberi (variante light)'}, format='json')
        self.assertEqual(clone_resp.status_code, status.HTTP_201_CREATED)
        cloned = Piatto.objects.get(nome='Risotto ai gamberi (variante light)')
        self.assertEqual(cloned.variante_di_id, estivo.id)
        self.assertEqual(cloned.allergeni.count(), 1)

    def test_create_menu_requires_structure_permission(self):
        # user senza membership sulla struttura
        other_user = User.objects.create_user(
            username='guest',
            password='password123',
            company=self.company,
            menu_creation_studio_enabled=True,
        )
        self.client.login(username='guest', password='password123')
        piatto = Piatto.objects.create(
            nome='Risotto allo Zafferano',
            categoria='primo',
            company=self.company,
            porzioni=1,
        )
        url = reverse('menu_generator_api:menu-list')
        data = {
            'nome': 'Menu Gala',
            'piatti': [piatto.id],
            'layout': None,
            'cavaliere_template': None,
            'struttura': self.structure.id,
            'data_evento': '2024-12-24',
            'turno': 'cena',
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_menu_with_permission(self):
        self.client.login(username='authorized', password='password123')
        piatto = Piatto.objects.create(
            nome='Risotto allo Zafferano',
            categoria='primo',
            company=self.company,
            porzioni=1,
        )
        url = reverse('menu_generator_api:menu-list')
        data = {
            'nome': 'Menu Gala',
            'piatti': [piatto.id],
            'layout': None,
            'cavaliere_template': None,
            'struttura': self.structure.id,
            'data_evento': '2024-12-24',
            'turno': 'cena',
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Menu.objects.count(), 1)

    def test_validate_menu_wizard_steps(self):
        self.client.login(username='authorized', password='password123')

        allergene = Allergene.objects.create(codice='A1', nome='Glutine')
        antipasto = Piatto.objects.create(
            nome='Bruschetta',
            categoria='antipasto',
            company=self.company,
            porzioni=1,
        )
        primo = Piatto.objects.create(
            nome='Risotto allo Zafferano',
            categoria='primo',
            company=self.company,
            porzioni=1,
        )
        primo.allergeni.add(allergene)
        secondo = Piatto.objects.create(
            nome='Tagliata di Manzo',
            categoria='secondo',
            company=self.company,
            porzioni=1,
        )
        dessert = Piatto.objects.create(
            nome='Tiramisù',
            categoria='dessert',
            company=self.company,
            porzioni=1,
        )

        url = reverse('menu_generator_api:menu-validate-menu')
        payload = {
            'nome': 'Menu Gala',
            'data_evento': '2025-12-24',
            'turno': 'cena',
            'struttura': self.structure.id,
            'layout': 10,
            'piatti': [antipasto.id, primo.id, secondo.id, dessert.id],
        }

        response = self.client.post(url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        steps = response.data['steps']
        self.assertEqual(steps['base']['status'], 'ok')
        self.assertEqual(steps['layout']['status'], 'ok')
        self.assertEqual(steps['piatti']['status'], 'ok')
        self.assertEqual(steps['allergeni']['status'], 'error')  # dessert senza allergeni
        self.assertFalse(response.data['can_publish'])

    def test_menu_insights_exposes_allergens_and_seasonality(self):
        self.client.login(username='authorized', password='password123')

        glutine = Allergene.objects.create(codice='A1', nome='Glutine')
        farina = Ingrediente.objects.create(nome='Farina', company=self.company, stagionalita='inverno')
        farina.allergeni.add(glutine)
        fragole = Ingrediente.objects.create(nome='Fragole', company=self.company, stagionalita='estate')

        primo = Piatto.objects.create(
            nome='Lasagna',
            categoria='primo',
            company=self.company,
            porzioni=1,
        )
        primo.ingredienti.add(farina)
        primo.allergeni.add(glutine)

        dessert = Piatto.objects.create(
            nome='Cheesecake alle fragole',
            categoria='dessert',
            company=self.company,
            porzioni=1,
        )
        dessert.ingredienti.add(fragole)

        menu = Menu.objects.create(
            nome='Menu Inverno',
            company=self.company,
            struttura=self.structure,
            creato_da=self.authorized_user,
            data_evento=date(2024, 12, 1),
        )
        menu.piatti.set([primo, dessert])

        url = reverse('menu_generator_api:menu-insights', args=[menu.id])
        response = self.client.get(url, {'reference_date': '2024-12-01'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        self.assertEqual(data['allergeni']['summary'][0]['conteggio'], 1)
        self.assertEqual(len(data['allergeni']['missing_allergeni']), 1)
        self.assertEqual(len(data['stagionalita']['fuori_stagione']), 1)
        self.assertTrue(data['suggestions'])

    def test_menu_versions_diff_and_restore(self):
        self.client.login(username='authorized', password='password123')

        piatto_one = Piatto.objects.create(
            nome='Bruschetta',
            categoria='antipasto',
            company=self.company,
            porzioni=1,
        )
        piatto_two = Piatto.objects.create(
            nome='Risotto allo Zafferano',
            categoria='primo',
            company=self.company,
            porzioni=1,
        )

        create_url = reverse('menu_generator_api:menu-list')
        menu_payload = {
            'nome': 'Menu Gala',
            'piatti': [piatto_one.id, piatto_two.id],
            'layout': None,
            'cavaliere_template': None,
            'struttura': self.structure.id,
            'data_evento': '2024-12-24',
            'turno': 'cena',
        }
        response = self.client.post(create_url, menu_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        menu_id = response.data['id']

        snapshot_url = reverse('menu_generator_api:menu-snapshot', args=[menu_id])
        snapshot_response = self.client.post(snapshot_url)
        self.assertEqual(snapshot_response.status_code, status.HTTP_201_CREATED)
        version_id = snapshot_response.data['id']

        update_url = reverse('menu_generator_api:menu-detail', args=[menu_id])
        updated_payload = {**menu_payload, 'piatti': [piatto_one.id]}
        update_response = self.client.put(update_url, updated_payload, format='json')
        self.assertEqual(update_response.status_code, status.HTTP_200_OK)

        diff_url = reverse('menu_generator_api:menu-version-diff', args=[menu_id, version_id])
        diff_response = self.client.get(diff_url)
        self.assertEqual(diff_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(diff_response.data['piatti']['removed']), 1)

        restore_url = reverse('menu_generator_api:menu-restore-version', args=[menu_id, version_id])
        restore_response = self.client.post(restore_url)
        self.assertEqual(restore_response.status_code, status.HTTP_200_OK)

        final_menu = self.client.get(update_url)
        self.assertEqual(len(final_menu.data['piatti']), 2)

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
    def test_async_document_job_completes_and_can_be_polled(self):
        self.client.login(username='authorized', password='password123')

        piatto = Piatto.objects.create(
            nome='Risotto allo Zafferano',
            categoria='primo',
            company=self.company,
            porzioni=1,
        )

        create_url = reverse('menu_generator_api:menu-list')
        menu_payload = {
            'nome': 'Menu Gala',
            'piatti': [piatto.id],
            'layout': None,
            'cavaliere_template': None,
            'struttura': self.structure.id,
            'data_evento': '2024-12-24',
            'turno': 'cena',
        }
        menu_response = self.client.post(create_url, menu_payload, format='json')
        self.assertEqual(menu_response.status_code, status.HTTP_201_CREATED)
        menu_id = menu_response.data['id']

        generate_url = reverse('menu_generator_api:menu-generate-documents', args=[menu_id])
        job_response = self.client.post(generate_url, {'format': 'docx', 'type': 'menu'})
        self.assertEqual(job_response.status_code, status.HTTP_202_ACCEPTED)
        job_id = job_response.data['id']

        job_detail_url = reverse('menu_generator_api:menu-document-job', args=[job_id])
        detail_response = self.client.get(job_detail_url)
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)

        job = MenuDocumentJob.objects.get(id=job_id)
        self.assertEqual(job.status, MenuDocumentJob.STATUS_SUCCESS)
        self.assertTrue(detail_response.data['download_url'])
        self.assertIsNotNone(detail_response.data['expires_at'])

    def test_document_health_endpoint_returns_status(self):
        self.client.login(username='authorized', password='password123')
        url = reverse('menu_generator_api:menu-document-health')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('worker_responding', response.data)

    def test_audit_trail_records_snapshot_and_restore(self):
        self.client.login(username='authorized', password='password123')
        piatto = Piatto.objects.create(
            nome='Risotto', categoria='primo', company=self.company, porzioni=1
        )
        create_url = reverse('menu_generator_api:menu-list')
        payload = {
            'nome': 'Audit Menu',
            'piatti': [piatto.id],
            'layout': None,
            'cavaliere_template': None,
            'struttura': self.structure.id,
            'data_evento': '2024-12-24',
            'turno': 'cena',
        }
        menu_response = self.client.post(create_url, payload, format='json')
        menu_id = menu_response.data['id']

        snapshot_url = reverse('menu_generator_api:menu-snapshot', args=[menu_id])
        snapshot_res = self.client.post(snapshot_url)
        version_id = snapshot_res.data['id']

        restore_url = reverse('menu_generator_api:menu-restore-version', args=[menu_id, version_id])
        self.client.post(restore_url)

        audit_url = reverse('menu_generator_api:menu-audit', args=[menu_id])
        audit_res = self.client.get(audit_url)
        self.assertEqual(audit_res.status_code, status.HTTP_200_OK)
        events_payload = audit_res.data['results'] if isinstance(audit_res.data, dict) and 'results' in audit_res.data else audit_res.data
        actions = [event['action'] for event in events_payload]
        self.assertIn('snapshot', actions)
        self.assertIn('restore', actions)

    def test_cleanup_task_removes_expired_jobs(self):
        piatto = Piatto.objects.create(nome='Test', categoria='primo', company=self.company)
        menu = Menu.objects.create(
            nome='Doc Menu',
            company=self.company,
            creato_da=self.authorized_user,
            struttura=self.structure,
            turno='cena',
        )
        menu.piatti.add(piatto)
        job = MenuDocumentJob.objects.create(
            menu=menu,
            created_by=self.authorized_user,
            output_format='pdf',
            doc_type='menu',
            status=MenuDocumentJob.STATUS_SUCCESS,
            completed_at=timezone.now() - timezone.timedelta(days=10),
            expires_at=timezone.now() - timezone.timedelta(days=1),
        )
        removed = cleanup_expired_documents_task()
        self.assertGreaterEqual(removed, 1)
        self.assertFalse(MenuDocumentJob.objects.filter(id=job.id).exists())

    def test_permissions_endpoint_returns_membership_summary(self):
        self.client.login(username='authorized', password='password123')

        url = reverse('menu_generator_api:permissions-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['aggregate']['can_edit_menus'])
        self.assertTrue(any(struct['permissions']['can_publish_menu'] for struct in response.data['structures']))
