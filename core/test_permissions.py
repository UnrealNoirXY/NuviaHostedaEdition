"""Test del layer di permessi centralizzato e della navigazione dichiarativa (Fase 1)."""

from django.test import TestCase, RequestFactory
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.contrib.auth.models import AnonymousUser

from accounts.models import User
from core.permissions import (
    Capability,
    CAPABILITY_RULES,
    user_can,
    capability_required,
)
from core.navigation import HUB_TOOLS, get_hub_tools


class UserCanTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_user(
            "su", "su@test.com", "pw", role=User.SUPERADMIN, is_superuser=True
        )
        cls.owner = User.objects.create_user(
            "owner", "owner@test.com", "pw", role=User.OWNER
        )
        cls.receptionist = User.objects.create_user(
            "rec", "rec@test.com", "pw", role=User.RECEPTIONIST
        )
        cls.inventory_user = User.objects.create_user(
            "inv", "inv@test.com", "pw", role=User.RECEPTIONIST, has_inventory_access=True
        )

    def test_anonymous_has_no_capability(self):
        anon = AnonymousUser()
        for cap in CAPABILITY_RULES:
            self.assertFalse(user_can(anon, cap), cap)

    def test_public_capability_for_any_authenticated_user(self):
        self.assertTrue(user_can(self.receptionist, Capability.IT_SUPPORT))
        self.assertTrue(user_can(self.receptionist, Capability.NUVIA_MAIL))
        self.assertTrue(user_can(self.receptionist, Capability.PROCEDURES))
        self.assertTrue(user_can(self.receptionist, Capability.HR_BACHECA))

    def test_flag_based_capability(self):
        # has_inventory_access concede INVENTORY, senza non si accede.
        self.assertTrue(user_can(self.inventory_user, Capability.INVENTORY))
        self.assertFalse(user_can(self.receptionist, Capability.INVENTORY))

    def test_role_based_capability(self):
        # OWNER accede a FINANCIALS, ECONOMATO e REVIEWS; il receptionist no.
        self.assertTrue(user_can(self.owner, Capability.FINANCIALS))
        self.assertTrue(user_can(self.owner, Capability.ECONOMATO))
        self.assertTrue(user_can(self.owner, Capability.REVIEWS))
        self.assertFalse(user_can(self.receptionist, Capability.FINANCIALS))
        self.assertFalse(user_can(self.receptionist, Capability.ECONOMATO))
        self.assertFalse(user_can(self.receptionist, Capability.REVIEWS))

    def test_superuser_bypasses_everything(self):
        for cap in CAPABILITY_RULES:
            self.assertTrue(user_can(self.superuser, cap), cap)

    def test_unknown_capability_raises(self):
        with self.assertRaises(KeyError):
            user_can(self.owner, "capacita_inesistente")


class CapabilityDecoratorTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user(
            "owner2", "owner2@test.com", "pw", role=User.OWNER
        )
        cls.receptionist = User.objects.create_user(
            "rec2", "rec2@test.com", "pw", role=User.RECEPTIONIST
        )
        cls.factory = RequestFactory()

    def _view(self):
        @capability_required(Capability.FINANCIALS)
        def view(request):
            return HttpResponse("ok")

        return view

    def test_decorator_allows_authorized(self):
        request = self.factory.get("/")
        request.user = self.owner
        response = self._view()(request)
        self.assertEqual(response.status_code, 200)

    def test_decorator_denies_unauthorized(self):
        request = self.factory.get("/")
        request.user = self.receptionist
        with self.assertRaises(PermissionDenied):
            self._view()(request)


class HubNavigationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_user(
            "su3", "su3@test.com", "pw", role=User.SUPERADMIN, is_superuser=True
        )
        cls.receptionist = User.objects.create_user(
            "rec3", "rec3@test.com", "pw", role=User.RECEPTIONIST
        )

    def test_every_hub_tool_uses_a_registered_capability(self):
        for tool in HUB_TOOLS:
            self.assertIn(tool.capability, CAPABILITY_RULES, tool.label)

    def test_superuser_sees_all_tools(self):
        labels = [t["label"] for t in get_hub_tools(self.superuser)]
        self.assertEqual(len(labels), len(HUB_TOOLS))

    def test_receptionist_sees_only_public_tools(self):
        labels = {t["label"] for t in get_hub_tools(self.receptionist)}
        # Strumenti pubblici sempre visibili
        self.assertIn("Supporto IT", labels)
        self.assertIn("Procedure Operative", labels)
        self.assertIn("Bacheca Nuvia", labels)
        # Strumenti riservati non visibili senza ruolo/flag
        self.assertNotIn("Controllo Amministrativo", labels)
        self.assertNotIn("Portale HR", labels)
        self.assertNotIn("Analisi Recensioni", labels)

    def test_tools_are_renderable(self):
        # as_context() chiama reverse(): verifica che tutti gli url_name esistano.
        for tool in get_hub_tools(self.superuser):
            self.assertTrue(tool["url"].startswith("/"), tool["label"])


class TemplateFilterTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user(
            "owner4", "owner4@test.com", "pw", role=User.OWNER
        )
        cls.receptionist = User.objects.create_user(
            "rec4", "rec4@test.com", "pw", role=User.RECEPTIONIST
        )

    def _render(self, user, capability):
        from django.template import Template, Context

        tpl = Template(
            "{% load custom_tags %}"
            "{% if user|user_can:cap %}SI{% else %}NO{% endif %}"
        )
        return tpl.render(Context({"user": user, "cap": capability})).strip()

    def test_filter_matches_user_can(self):
        self.assertEqual(self._render(self.owner, Capability.FINANCIALS), "SI")
        self.assertEqual(self._render(self.receptionist, Capability.FINANCIALS), "NO")

    def test_filter_unknown_capability_is_falsey(self):
        self.assertEqual(self._render(self.owner, "inesistente"), "NO")


class SidebarCapabilityGatingTests(TestCase):
    """La sidebar (partials/_sidebar.html) gate-a le voci tramite user_can:
    verifica end-to-end che il filtro template controlli la visibilità."""

    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_user(
            "su5", "su5@test.com", "pw", role=User.SUPERADMIN, is_superuser=True
        )
        cls.owner = User.objects.create_user(
            "owner5", "owner5@test.com", "pw", role=User.OWNER
        )
        cls.receptionist = User.objects.create_user(
            "rec5", "rec5@test.com", "pw", role=User.RECEPTIONIST
        )
        cls.corporate = User.objects.create_user(
            "corp5", "corp5@test.com", "pw", role=User.CORPORATE
        )

    def _render_sidebar(self, user):
        from django.template.loader import render_to_string
        from django.test import RequestFactory

        request = RequestFactory().get("/hub/")
        request.user = user
        return render_to_string(
            "partials/_sidebar.html",
            {"user": user, "platform_name": "Nuvia"},
            request=request,
        )

    def test_receptionist_does_not_see_restricted_items(self):
        html = self._render_sidebar(self.receptionist)
        for label in (
            "Portale HR",
            "Economato",
            "Controllo Amministrativo",
            "Schede Profilo Wallet",
            "Inventario",
        ):
            self.assertNotIn(label, html, label)

    def test_owner_sees_role_based_items(self):
        html = self._render_sidebar(self.owner)
        for label in ("Portale HR", "Economato", "Controllo Amministrativo"):
            self.assertIn(label, html, label)

    def test_reviews_role_controls_reviews_menu(self):
        # Recensioni è role-based: un ruolo abilitato (CORPORATE) la vede, il receptionist no.
        self.assertIn("Recensioni", self._render_sidebar(self.corporate))
        self.assertNotIn("Recensioni", self._render_sidebar(self.receptionist))

    def test_superuser_sees_profile_cards(self):
        self.assertIn("Schede Profilo Wallet", self._render_sidebar(self.superuser))
