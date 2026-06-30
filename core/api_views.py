from django.urls import NoReverseMatch, reverse
from django.utils.functional import cached_property
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from core.templatetags.custom_tags import get_avatar_url


class MobileShellContextView(APIView):
    """Expose a structured navigation context for the mobile command shell."""

    permission_classes = [IsAuthenticated]
    VOICE_SEARCH_ENDPOINT = '/api/voice-search'

    def _reverse(self, name, *args, **kwargs):
        try:
            return reverse(name, args=args, kwargs=kwargs)
        except NoReverseMatch:
            return None

    def _add_nav_item(self, items, *, href, label, icon, section='navigation', depth=0, quick=True):
        if not href:
            return
        items.append(
            {
                'href': href,
                'label': label,
                'iconClass': icon,
                'section': section,
                'depth': depth,
                'quickActionEligible': quick,
            }
        )

    def _navigation(self):
        user = self.request.user
        items = []

        # Navigation section
        self._add_nav_item(
            items,
            href=self._reverse('home'),
            label='Hub',
            icon='fas fa-home',
            section='navigation',
        )
        self._add_nav_item(
            items,
            href=self._reverse('desk:home'),
            label='Home Desk',
            icon='fas fa-desktop',
            section='navigation',
        )

        if user.is_superuser or getattr(user, 'has_bookings_access', False):
            self._add_nav_item(
                items,
                href=self._reverse('bookings:dashboard'),
                label='Cruscotto Check-in',
                icon='fas fa-calendar-check',
                section='navigation',
            )

        self._add_nav_item(
            items,
            href=self._reverse('procedures:procedure_list'),
            label='Procedure',
            icon='fas fa-book-open',
            section='navigation',
        )

        self._add_nav_item(
            items,
            href=self._reverse('hr_portal:portal'),
            label='Portale HR',
            icon='fas fa-id-badge',
            section='navigation',
        )

        if user.is_superuser or user.role in {
            User.OWNER,
            User.DIRECTOR,
            User.CORPORATE,
            User.CAPO_ECONOMO,
            User.RISORSE_UMANE,
            User.HEAD_MAINTAINER,
        }:
            self._add_nav_item(
                items,
                href=self._reverse('core:director_cockpit'),
                label='Cruscotto Direzione',
                icon='fas fa-tachometer-alt',
                section='navigation',
            )

        if getattr(user, 'has_inventory_access', False):
            self._add_nav_item(
                items,
                href=self._reverse('inventory:list'),
                label='Inventario',
                icon='fas fa-boxes-stacked',
                section='navigation',
            )

        if user.is_superuser or user.role in {
            User.OWNER,
            User.CAPO_ECONOMO,
            User.ECONOMO,
            User.DIRECTOR,
        }:
            self._add_nav_item(
                items,
                href=self._reverse('economato:app'),
                label='Economato',
                icon='fas fa-warehouse',
                section='navigation',
            )

        if user.is_superuser or user.role in {
            User.SUPERADMIN,
            User.OWNER,
            User.DIRECTOR,
            User.ADMINISTRATIVE,
        }:
            self._add_nav_item(
                items,
                href=self._reverse('financials:dashboard'),
                label='Controllo Amministrativo',
                icon='fas fa-chart-line',
                section='navigation',
            )

        if user.is_superuser:
            self._add_nav_item(
                items,
                href=self._reverse('communications:scheduled_report_list'),
                label='Report Programmati',
                icon='fas fa-envelope-open-text',
                section='navigation',
                quick=False,
            )

        # Tools section
        if user.is_superuser or user.role in {User.CORPORATE, User.RISORSE_UMANE}:
            self._add_nav_item(
                items,
                href=self._reverse('communications:create'),
                label='Crea Comunicazione',
                icon='fas fa-bullhorn',
                section='tools',
            )

        if user.is_superuser or getattr(user, 'has_maintenance_access', False):
            self._add_nav_item(
                items,
                href=self._reverse('maintenance_tool_home'),
                label='Manutenzione',
                icon='fas fa-wrench',
                section='tools',
            )

        if user.is_superuser or user.role == User.IT_TECHNICIAN or getattr(
            user, 'has_it_support_management_access', False
        ):
            self._add_nav_item(
                items,
                href=self._reverse('it_support:it_ticket_management_list'),
                label='Supporto IT · Dashboard',
                icon='fas fa-tasks',
                section='tools',
                depth=1,
            )
            self._add_nav_item(
                items,
                href=self._reverse('assets:asset-list'),
                label='Gestione Asset',
                icon='fas fa-database',
                section='tools',
                depth=1,
            )
            self._add_nav_item(
                items,
                href=self._reverse('it_support:it-reporting-dashboard'),
                label='Report IT',
                icon='fas fa-chart-pie',
                section='tools',
                depth=1,
            )
        else:
            self._add_nav_item(
                items,
                href=self._reverse('it_support:it_ticket_list'),
                label='Supporto IT',
                icon='fas fa-headset',
                section='tools',
            )

        if user.is_superuser or user.role in {User.ADMINISTRATIVE, User.RISORSE_UMANE}:
            self._add_nav_item(
                items,
                href=self._reverse('documents:document_list'),
                label='Amministrazione',
                icon='fas fa-file-invoice',
                section='tools',
            )

        if getattr(user, 'can_manage_purchase_orders', False):
            self._add_nav_item(
                items,
                href=self._reverse('purchase_orders:list'),
                label="Buoni d'Ordine",
                icon='fas fa-shopping-cart',
                section='tools',
            )

        if user.is_superuser or getattr(user, 'has_reviews_access', False):
            self._add_nav_item(
                items,
                href=self._reverse('reviews:analysis_center'),
                label='Recensioni · Centro Analisi',
                icon='fas fa-chart-pie',
                section='reviews',
            )
            self._add_nav_item(
                items,
                href=self._reverse('reviews:dashboard'),
                label='Recensioni · Dashboard',
                icon='fas fa-chart-bar',
                section='reviews',
            )
            if user.role == User.SUPERADMIN:
                self._add_nav_item(
                    items,
                    href=self._reverse('reviews:scraping_panel'),
                    label='Recensioni · Scraper',
                    icon='fas fa-play-circle',
                    section='reviews',
                    depth=1,
                    quick=False,
                )
            if user.is_superuser:
                self._add_nav_item(
                    items,
                    href=self._reverse('reviews:report_builder'),
                    label='Recensioni · Reporting',
                    icon='fas fa-file-alt',
                    section='reviews',
                    depth=1,
                    quick=False,
                )

        return items

    @cached_property
    def context_payload(self):
        user = self.request.user
        navigation = self._navigation()
        quick_defaults = [item['href'] for item in navigation if item.get('quickActionEligible')][:4]

        return {
            'user': {
                'id': user.id,
                'fullName': user.get_full_name() or user.username,
                'role': user.role,
                'isSuperuser': user.is_superuser,
                'company': user.company_id,
                'resort': user.resort_id,
                'avatarUrl': get_avatar_url(user),
            },
            'shortcuts': {
                'hub': self._reverse('home'),
                'desk': self._reverse('desk:home'),
                'maintenance': self._reverse('ticket_create'),
                'profile': self._reverse('profile'),
                'logout': self._reverse('logout'),
                'voiceSearch': self.VOICE_SEARCH_ENDPOINT,
            },
            'navigation': navigation,
            'quickActionsDefaults': quick_defaults,
        }

    def get(self, request, *args, **kwargs):
        return Response(self.context_payload)
