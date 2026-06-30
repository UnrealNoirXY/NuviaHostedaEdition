"""Viste e API per il Menu Creation Studio."""

import json
import logging
from collections import Counter, defaultdict
from math import ceil
from datetime import date
from django.contrib.auth.mixins import AccessMixin
from django.conf import settings
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.utils.text import slugify
from django.views import View
from django.views.generic import TemplateView, DetailView
from django.db.models import Q
from rest_framework import permissions, viewsets, status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from celery import current_app

from clients.models import Company, Structure, StructureMembership

logger = logging.getLogger(__name__)

from .documents import build_cavalieri_docx, build_menu_docx, build_menu_pdf, build_menu_bundle
from .models import (
    Allergene,
    Ingrediente,
    BaseFoodItem,
    Piatto,
    LayoutTemplate,
    CavaliereTemplate,
    Menu,
    MenuVersion,
    MenuDocumentJob,
    MenuAuditEvent,
)
from .serializers import (
    AllergeneSerializer,
    IngredienteSerializer,
    BaseFoodItemSerializer,
    PiattoSerializer,
    PiattoListSerializer,
    LayoutTemplateSerializer,
    CavaliereTemplateSerializer,
    MenuSerializer,
    MenuVersionSerializer,
    MenuDocumentJobSerializer,
    MenuAuditEventSerializer,
)
from .tasks import generate_menu_documents_task


def _active_structure_membership(user, structure):
    """Restituisce la membership attiva dell'utente per la struttura indicata."""

    today = date.today()
    return (
        user.structure_memberships.select_related('role')
        .filter(
            structure=structure,
            is_active=True,
            valid_from__lte=today,
        )
        .filter(Q(valid_to__isnull=True) | Q(valid_to__gte=today))
        .first()
    )


def _is_effectively_superuser(user):
    """Verifica se l'utente è superuser Django o ha il ruolo 'superadmin'."""
    return user.is_superuser or getattr(user, "role", None) == "superadmin"


def user_has_structure_permission(user, structure, perm_name):
    if _is_effectively_superuser(user):
        return True
    if structure is None:
        return False
    user_role = getattr(user, "role", None)
    if user_role == "owner" and user.company_id == structure.company_id:
        return True

    today = date.today()
    memberships_qs = user.structure_memberships.filter(
        is_active=True, valid_from__lte=today
    ).filter(Q(valid_to__isnull=True) | Q(valid_to__gte=today))

    if user_role == "chef" and user.company_id == structure.company_id:
        membership = memberships_qs.filter(structure=structure).first()
        if membership:
             return getattr(membership.role, perm_name, True)

        # Se ha altre memberships in altre strutture della stessa company,
        # allora NON ha permessi su questa struttura (isolamento)
        if memberships_qs.filter(structure__company_id=user.company_id).exists():
            return False

        # Se non ha alcuna membership ma è Chef della company, permettiamo edit base
        if perm_name in ['can_edit_menus', 'can_edit_dishes', 'can_manage_allergens']:
            return True

    membership = memberships_qs.filter(structure=structure).first()
    if not membership or not membership.role:
        return False
    return getattr(membership.role, perm_name, False)


def user_has_company_permission(user, company, perm_name):
    if _is_effectively_superuser(user):
        return True
    if company and getattr(user, "role", None) == "owner" and user.company_id == company.id:
        return True
    today = date.today()
    return user.structure_memberships.filter(
        structure__company=company,
        is_active=True,
        valid_from__lte=today,
    ).filter(
        Q(valid_to__isnull=True) | Q(valid_to__gte=today)
    ).filter(**{f"role__{perm_name}": True}).exists()


def user_has_any_membership(user):
    if _is_effectively_superuser(user):
        return True
    if getattr(user, "role", None) in ["owner", "chef"] and user.company_id:
        return True
    today = date.today()
    return user.structure_memberships.filter(
        is_active=True,
        valid_from__lte=today,
    ).filter(Q(valid_to__isnull=True) | Q(valid_to__gte=today)).exists()


class MenuStudioPermissionMixin(AccessMixin):
    """Mixin per verificare i permessi di accesso allo studio."""

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        if not user.is_authenticated:
            return self.handle_no_permission()
        if not (_is_effectively_superuser(user) or user.menu_creation_studio_enabled or user.role in ["owner", "chef"]):
            return self.handle_no_permission()
        if not user_has_any_membership(user):
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)


class MenuCreationStudioView(MenuStudioPermissionMixin, TemplateView):
    template_name = "menu_generator/studio.html"


class GenerateMenuDocumentView(MenuStudioPermissionMixin, View):
    """Genera PDF/Docx/ZIP per menu e cavalieri."""

    def get(self, request, *args, **kwargs):
        menu = get_object_or_404(Menu, id=kwargs.get('menu_id'))

        if request.user.company != menu.company and not _is_effectively_superuser(request.user):
            raise Http404

        doc_type = request.GET.get('type', 'menu')  # menu | cavaliere
        output_format = request.GET.get('format', 'pdf')  # pdf | docx | zip
        include_cavalieri = request.GET.get('include_cavalieri') in {"1", "true", "True"}

        if output_format == 'docx':
            return self._build_docx_response(menu, doc_type)
        if output_format == 'zip':
            return self._build_zip_response(menu, doc_type, include_cavalieri)
        return self._build_pdf_response(menu, doc_type)

    def _group_piatti(self, menu):
        grouped = defaultdict(list)
        for piatto in menu.piatti.order_by('categoria', 'nome'):
            grouped[piatto.get_categoria_display()].append(piatto)
        return grouped

    def _render_pdf_bytes(self, menu, doc_type):
        pdf_bytes, _ = build_menu_pdf(menu, doc_type)
        return pdf_bytes

    def _build_pdf_response(self, menu, doc_type):
        pdf_bytes = self._render_pdf_bytes(menu, doc_type)
        filename = f"{slugify(menu.nome)}_{doc_type}.pdf"
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{filename}"'
        return response

    def _build_docx_response(self, menu, doc_type):
        if doc_type == 'cavaliere':
            buffer, filename = build_cavalieri_docx(menu)
        else:
            buffer, filename = build_menu_docx(menu)
        response = HttpResponse(
            buffer.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    def _build_zip_response(self, menu, doc_type, include_cavalieri):
        bundle, filename = build_menu_bundle(menu, doc_type, include_cavalieri)
        response = HttpResponse(bundle.getvalue(), content_type='application/zip')
        response['Content-Disposition'] = (
            f'attachment; filename="{filename}"'
        )
        return response


class CanAccessMenuGenerator(permissions.BasePermission):
    """Permesso base per lo studio menu."""

    def has_permission(self, request, view):
        user = request.user
        if not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        if not (user.menu_creation_studio_enabled or user.role in ["owner", "chef"]):
            return False
        return user_has_any_membership(user)


class PermissionSummaryViewSet(viewsets.ViewSet):
    """Restituisce i permessi aggregati e per struttura dell'utente corrente."""

    permission_classes = [CanAccessMenuGenerator]

    def list(self, request):
        today = date.today()
        is_owner = request.user.role == "owner"
        is_chef = request.user.role == "chef"
        is_superuser = _is_effectively_superuser(request.user)

        tracked_perms = [
            'can_edit_menus',
            'can_publish_menu',
            'can_approve_menu',
            'can_edit_layouts',
            'can_edit_dishes',
            'can_manage_allergens',
            'can_manage_templates',
        ]

        if is_superuser:
            structures_qs = Structure.objects.select_related('company').all().order_by('company__name', 'name')
            full_perms = {perm: True for perm in tracked_perms}
            structures = [
                {
                    'id': structure.id,
                    'name': structure.name,
                    'company_id': structure.company_id,
                    'company_name': structure.company.name,
                    'role': 'Super Admin',
                    'permissions': full_perms,
                }
                for structure in structures_qs
            ]
            aggregate = full_perms
            companies = list(Company.objects.values('id', 'name').order_by('name'))
            structures_scope = [
                {
                    'id': s['id'],
                    'name': s['name'],
                    'company_id': s['company_id'],
                    'company_name': s['company_name'],
                }
                for s in structures
            ]
        elif (is_owner or is_chef) and request.user.company_id:
            structures_qs = Structure.objects.select_related('company').filter(
                company_id=request.user.company_id
            ).order_by('name')

            # Se è Chef, verifichiamo se ha membership specifiche o se vede tutto
            memberships = StructureMembership.objects.filter(
                user=request.user, is_active=True, valid_from__lte=today
            ).filter(Q(valid_to__isnull=True) | Q(valid_to__gte=today))

            assigned_structure_ids = set(memberships.values_list('structure_id', flat=True))

            full_perms = {perm: True for perm in tracked_perms}
            # Se è Chef e non ha membership, gli diamo permessi base su tutto della sua company
            # Se ha membership, filtriamo o evidenziamo quelle assegnate

            structures = []
            for structure in structures_qs:
                role_name = 'Proprietario' if is_owner else 'Chef'
                perms = full_perms.copy()

                # Se è Chef, limitiamo i permessi se non è la sua struttura assegnata (opzionale, basato su requisiti)
                # Per ora, se è Chef della company, permettiamo la selezione.

                structures.append({
                    'id': structure.id,
                    'name': structure.name,
                    'company_id': structure.company_id,
                    'company_name': structure.company.name,
                    'role': role_name,
                    'permissions': perms,
                    'is_assigned': structure.id in assigned_structure_ids if is_chef else True
                })

            aggregate = full_perms
            companies = [{'id': request.user.company_id, 'name': request.user.company.name}]
            structures_scope = [
                {
                    'id': s['id'],
                    'name': s['name'],
                    'company_id': s['company_id'],
                    'company_name': s['company_name'],
                }
                for s in structures if (not is_chef or not assigned_structure_ids or s['id'] in assigned_structure_ids)
            ]
        else:
            memberships = (
                StructureMembership.objects.select_related('structure', 'structure__company', 'role')
                .filter(
                    user=request.user,
                    is_active=True,
                    valid_from__lte=today,
                )
                .filter(Q(valid_to__isnull=True) | Q(valid_to__gte=today))
            )

            structures = []
            for membership in memberships:
                structures.append(
                    {
                        'id': membership.structure.id,
                        'name': membership.structure.name,
                        'company_id': membership.structure.company_id,
                        'company_name': membership.structure.company.name,
                        'role': membership.role.name if membership.role else None,
                        'permissions': membership.permissions,
                    }
                )

            aggregate = {
                perm: any((struct['permissions'] or {}).get(perm) for struct in structures)
                for perm in tracked_perms
            }

            companies_map = {}
            for item in structures:
                companies_map[item['company_id']] = item['company_name']
            companies = [
                {'id': company_id, 'name': name}
                for company_id, name in companies_map.items()
            ]
            structures_scope = [
                {
                    'id': item['id'],
                    'name': item['name'],
                    'company_id': item['company_id'],
                    'company_name': item['company_name'],
                }
                for item in structures
            ]

        return Response(
            {
                'structures': structures,
                'companies': companies,
                'structures_scope': structures_scope,
                'aggregate': aggregate,
                'is_owner': is_owner,
                'is_superuser': is_superuser,
            }
        )


class AllergeneViewSet(viewsets.ModelViewSet):
    queryset = Allergene.objects.all()
    serializer_class = AllergeneSerializer
    permission_classes = [CanAccessMenuGenerator]

    def get_queryset(self):
        user = self.request.user
        if _is_effectively_superuser(user):
            qs = Allergene.objects.all()
            company_id = self.request.query_params.get('company')
            if company_id:
                qs = qs.filter(company_id=company_id)
        else:
            qs = Allergene.objects.filter(Q(company=user.company) | Q(company__isnull=True))

        search_query = self.request.query_params.get('search')
        if search_query:
            qs = qs.filter(
                Q(nome__icontains=search_query)
                | Q(codice__icontains=search_query)
                | Q(descrizione__icontains=search_query)
            )
        return qs

    def perform_create(self, serializer):
        user = self.request.user
        company = user.company
        if _is_effectively_superuser(user):
             # In case of superuser, try to get company from data if provided
             company_id = self.request.data.get('company')
             if company_id:
                 company = get_object_or_404(Company, pk=company_id)

        if not user_has_company_permission(user, company, 'can_manage_allergens'):
            raise PermissionDenied("Non hai i permessi per gestire gli allergeni.")
        serializer.save(company=company)

    def perform_update(self, serializer):
        if not user_has_company_permission(
            self.request.user, self.request.user.company, 'can_manage_allergens'
        ):
            raise PermissionDenied("Non hai i permessi per gestire gli allergeni.")
        serializer.save()

    def perform_destroy(self, instance):
        if not user_has_company_permission(
            self.request.user, self.request.user.company, 'can_manage_allergens'
        ):
            raise PermissionDenied("Non hai i permessi per eliminare gli allergeni.")
        instance.delete()


class IngredienteViewSet(viewsets.ModelViewSet):
    queryset = Ingrediente.objects.all()
    serializer_class = IngredienteSerializer
    permission_classes = [CanAccessMenuGenerator]

    def get_queryset(self):
        user = self.request.user
        if _is_effectively_superuser(user):
            qs = Ingrediente.objects.all()
            company_id = self.request.query_params.get('company')
            if company_id:
                qs = qs.filter(company_id=company_id)
        else:
            qs = Ingrediente.objects.filter(company=user.company)

        search_query = self.request.query_params.get('search')
        if search_query:
            qs = qs.filter(
                Q(nome__icontains=search_query)
                | Q(descrizione__icontains=search_query)
            )
        return qs

    def perform_create(self, serializer):
        user = self.request.user
        company = user.company
        if _is_effectively_superuser(user):
             company_id = self.request.data.get('company')
             if company_id:
                 company = get_object_or_404(Company, pk=company_id)

        if not user_has_company_permission(user, company, 'can_manage_allergens'):
            raise PermissionDenied("Non hai i permessi per gestire gli ingredienti.")
        serializer.save(company=company)

    def perform_update(self, serializer):
        if not user_has_company_permission(
            self.request.user, self.request.user.company, 'can_manage_allergens'
        ):
            raise PermissionDenied("Non hai i permessi per gestire gli ingredienti.")
        serializer.save()

    def perform_destroy(self, instance):
        if not user_has_company_permission(
            self.request.user, self.request.user.company, 'can_manage_allergens'
        ):
            raise PermissionDenied("Non hai i permessi per eliminare gli ingredienti.")
        instance.delete()


class BaseFoodItemViewSet(viewsets.ModelViewSet):
    queryset = BaseFoodItem.objects.all()
    serializer_class = BaseFoodItemSerializer
    permission_classes = [CanAccessMenuGenerator]

    def get_queryset(self):
        user = self.request.user
        if _is_effectively_superuser(user):
            qs = BaseFoodItem.objects.all()
            company_id = self.request.query_params.get('company')
            if company_id:
                qs = qs.filter(company_id=company_id)
            return qs
        return BaseFoodItem.objects.filter(company=user.company)

    def perform_create(self, serializer):
        user = self.request.user
        company = user.company
        if _is_effectively_superuser(user):
             company_id = self.request.data.get('company')
             if company_id:
                 company = get_object_or_404(Company, pk=company_id)

        if not user_has_company_permission(user, company, 'can_manage_allergens'):
            raise PermissionDenied("Non hai i permessi per gestire gli alimenti base.")
        serializer.save(company=company)

    def perform_update(self, serializer):
        if not user_has_company_permission(
            self.request.user, self.request.user.company, 'can_manage_allergens'
        ):
            raise PermissionDenied("Non hai i permessi per gestire gli alimenti base.")
        serializer.save()

    def perform_destroy(self, instance):
        if not user_has_company_permission(
            self.request.user, self.request.user.company, 'can_manage_allergens'
        ):
            raise PermissionDenied("Non hai i permessi per eliminare gli alimenti base.")
        instance.delete()


class PiattoViewSet(viewsets.ModelViewSet):
    queryset = Piatto.objects.all().prefetch_related('ingredienti', 'allergeni')
    permission_classes = [CanAccessMenuGenerator]

    def get_serializer_class(self):
        if self.action == 'list':
            detailed = self.request.query_params.get('detailed')
            if str(detailed).lower() in {'1', 'true', 'yes'}:
                return PiattoSerializer
            return PiattoListSerializer
        return PiattoSerializer

    def get_queryset(self):
        user = self.request.user
        if _is_effectively_superuser(user):
            qs = Piatto.objects.all()
            company_id = self.request.query_params.get('company')
            if company_id:
                qs = qs.filter(company_id=company_id)
        else:
            qs = Piatto.objects.filter(company=user.company)

        if self.action in {'list', 'retrieve'}:
            qs = qs.select_related('company', 'base_item', 'variante_di').prefetch_related(
                'ingredienti__allergeni',
                'allergeni',
            )

        if self.action == 'list':
            categorie = self.request.query_params.getlist('categoria')
            categoria_str = self.request.query_params.get('categorie')
            if categoria_str:
                categorie.extend([c for c in categoria_str.split(',') if c])
            if categorie:
                qs = qs.filter(categoria__in=categorie)

            stagionalita = self.request.query_params.get('stagionalita')
            if stagionalita:
                qs = qs.filter(stagionalita=stagionalita)

            include_allergeni = self.request.query_params.get('allergeni')
            if include_allergeni:
                ids = [int(a) for a in include_allergeni.split(',') if a.isdigit()]
                if ids:
                    qs = qs.filter(allergeni__id__in=ids)

            exclude_allergeni = self.request.query_params.get('exclude_allergeni')
            if exclude_allergeni:
                ids = [int(a) for a in exclude_allergeni.split(',') if a.isdigit()]
                if ids:
                    qs = qs.exclude(allergeni__id__in=ids)

            ingredienti = self.request.query_params.get('ingredienti')
            if ingredienti:
                ids = [int(i) for i in ingredienti.split(',') if i.isdigit()]
                if ids:
                    qs = qs.filter(ingredienti__id__in=ids)

            include_inactive = self.request.query_params.get('include_inactive')
            if str(include_inactive).lower() not in {'1', 'true', 'yes'}:
                qs = qs.filter(is_active=True)

            search_query = self.request.query_params.get('search')
            if search_query:
                qs = qs.filter(
                    Q(nome__icontains=search_query)
                    | Q(descrizione__icontains=search_query)
                    | Q(ingredienti__nome__icontains=search_query)
                )

            return qs.distinct()

        return qs

    def perform_create(self, serializer):
        user = self.request.user
        company = user.company
        if _is_effectively_superuser(user):
             company_id = self.request.data.get('company')
             if company_id:
                 company = get_object_or_404(Company, pk=company_id)

        if not user_has_company_permission(user, company, 'can_edit_dishes'):
            raise PermissionDenied("Non hai i permessi per creare piatti.")
        serializer.save(company=company)

    def perform_update(self, serializer):
        if not user_has_company_permission(
            self.request.user, self.request.user.company, 'can_edit_dishes'
        ):
            raise PermissionDenied("Non hai i permessi per aggiornare i piatti.")
        serializer.save()

    def perform_destroy(self, instance):
        if not user_has_company_permission(
            self.request.user, self.request.user.company, 'can_edit_dishes'
        ):
            raise PermissionDenied("Non hai i permessi per eliminare i piatti.")
        instance.delete()

    @action(detail=True, methods=['post'])
    def clone(self, request, pk=None):
        if not user_has_company_permission(
            request.user, request.user.company, 'can_edit_dishes'
        ):
            raise PermissionDenied("Non hai i permessi per duplicare i piatti.")

        original = self.get_object()
        clone_name = request.data.get('nome') or f"{original.nome} (variante)"

        cloned = Piatto.objects.create(
            nome=clone_name,
            descrizione=original.descrizione,
            categoria=original.categoria,
            company=request.user.company,
            allergen_summary=original.allergen_summary,
            base_item=original.base_item,
            variante_di=original,
            stagionalita=original.stagionalita,
            tempo_preparazione_minuti=original.tempo_preparazione_minuti,
            tempo_cottura_minuti=original.tempo_cottura_minuti,
            porzioni=original.porzioni,
            prezzo=original.prezzo,
            note_internal=original.note_internal,
        )
        cloned.ingredienti.set(original.ingredienti.all())
        cloned.allergeni.set(original.allergeni.all())

        serializer = PiattoSerializer(cloned, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class LayoutTemplateViewSet(viewsets.ModelViewSet):
    queryset = LayoutTemplate.objects.all()
    serializer_class = LayoutTemplateSerializer
    permission_classes = [CanAccessMenuGenerator]

    def get_queryset(self):
        user = self.request.user
        if _is_effectively_superuser(user):
            qs = LayoutTemplate.objects.all()
            company_id = self.request.query_params.get('company')
            if company_id:
                qs = qs.filter(company_id=company_id)
        else:
            if user.company:
                qs = LayoutTemplate.objects.filter(company=user.company)
                if user.role == 'chef':
                    today = date.today()
                    assigned_ids = user.structure_memberships.filter(
                        is_active=True, valid_from__lte=today
                    ).filter(Q(valid_to__isnull=True) | Q(valid_to__gte=today)).values_list('structure_id', flat=True)
                    if assigned_ids.exists():
                        qs = qs.filter(Q(struttura_id__in=assigned_ids) | Q(struttura__isnull=True))
            else:
                qs = LayoutTemplate.objects.none()

        struttura_id = self.request.query_params.get('struttura') or self.request.query_params.get('structure')
        if struttura_id:
            qs = qs.filter(struttura_id=struttura_id)
        return qs

    def perform_create(self, serializer):
        company = getattr(self.request.user, 'company', None)
        if not company and _is_effectively_superuser(self.request.user):
            company_id = self.request.data.get('company')
            if company_id:
                company = get_object_or_404(Company, pk=company_id)
        if not company:
            raise ValidationError({'company': ['Selezionare una company valida.']})
        struttura_id = self.request.data.get('struttura')
        struttura = None
        if struttura_id:
            struttura = get_object_or_404(Structure, pk=struttura_id, company=company)
        if not user_has_company_permission(
            self.request.user, company, 'can_edit_layouts'
        ):
            raise PermissionDenied("Non hai i permessi per creare layout.")
        serializer.save(company=company, creato_da=self.request.user, struttura=struttura)

    def perform_update(self, serializer):
        # Supporta il parsing manuale di JSON inviato come FormData per gestire upload file
        if 'struttura_blocchi' in self.request.data and isinstance(self.request.data['struttura_blocchi'], str):
            try:
                serializer.validated_data['struttura_blocchi'] = json.loads(self.request.data['struttura_blocchi'])
            except Exception:
                pass
        if 'metadata' in self.request.data and isinstance(self.request.data['metadata'], str):
            try:
                serializer.validated_data['metadata'] = json.loads(self.request.data['metadata'])
            except Exception:
                pass

        if not user_has_company_permission(
            self.request.user, self.request.user.company, 'can_edit_layouts'
        ):
            raise PermissionDenied("Non hai i permessi per aggiornare layout.")
        serializer.save()


class CavaliereTemplateViewSet(viewsets.ModelViewSet):
    queryset = CavaliereTemplate.objects.all()
    serializer_class = CavaliereTemplateSerializer
    permission_classes = [CanAccessMenuGenerator]

    def get_queryset(self):
        user = self.request.user
        if _is_effectively_superuser(user):
            return CavaliereTemplate.objects.all()
        return CavaliereTemplate.objects.filter(company=user.company)

    def perform_create(self, serializer):
        user = self.request.user
        company = user.company
        if _is_effectively_superuser(user):
            company_id = self.request.data.get('company')
            if company_id:
                company = get_object_or_404(Company, pk=company_id)

        if not user_has_company_permission(user, company, 'can_manage_templates'):
            raise PermissionDenied("Non hai i permessi per creare template cavalieri.")
        serializer.save(company=company, creato_da=user)

    def perform_update(self, serializer):
        if not user_has_company_permission(
            self.request.user, self.request.user.company, 'can_manage_templates'
        ):
            raise PermissionDenied("Non hai i permessi per aggiornare template cavalieri.")
        serializer.save()

    def perform_destroy(self, instance):
        if not user_has_company_permission(
            self.request.user, self.request.user.company, 'can_manage_templates'
        ):
            raise PermissionDenied("Non hai i permessi per eliminare template cavalieri.")
        instance.delete()


class MenuViewSet(viewsets.ModelViewSet):
    queryset = Menu.objects.all().select_related('layout', 'cavaliere_template', 'struttura')
    serializer_class = MenuSerializer
    permission_classes = [CanAccessMenuGenerator]

    def get_queryset(self):
        user = self.request.user
        if _is_effectively_superuser(user):
            qs = Menu.objects.all()
            company_id = self.request.query_params.get('company')
            if company_id:
                qs = qs.filter(company_id=company_id)
        else:
            qs = Menu.objects.filter(company=user.company)
            if user.role == 'chef':
                today = date.today()
                assigned_ids = user.structure_memberships.filter(
                    is_active=True, valid_from__lte=today
                ).filter(Q(valid_to__isnull=True) | Q(valid_to__gte=today)).values_list('structure_id', flat=True)
                if assigned_ids.exists():
                    qs = qs.filter(struttura_id__in=assigned_ids)

        struttura_id = self.request.query_params.get('struttura')
        if struttura_id:
            qs = qs.filter(struttura_id=struttura_id)
        turno = self.request.query_params.get('turno')
        if turno:
            qs = qs.filter(turno=turno)
        return qs

    def _ensure_structure_permission(self, menu, perm_name='can_edit_menus'):
        if menu.struttura is None:
            return
        if not user_has_structure_permission(self.request.user, menu.struttura, perm_name):
            raise PermissionDenied("Non hai i permessi per gestire i menu di questa struttura.")

    def perform_create(self, serializer):
        struttura = serializer.validated_data.get('struttura')
        if not user_has_structure_permission(self.request.user, struttura, 'can_edit_menus'):
            raise PermissionDenied("Non hai i permessi per creare menu per questa struttura.")

        company = struttura.company if struttura else self.request.user.company
        serializer.save(company=company, creato_da=self.request.user)

    def perform_update(self, serializer):
        menu = serializer.instance
        struttura = serializer.validated_data.get('struttura', menu.struttura)
        if not user_has_structure_permission(self.request.user, struttura, 'can_edit_menus'):
            raise PermissionDenied("Non hai i permessi per aggiornare questo menu.")
        serializer.save()

    def perform_destroy(self, instance):
        self._ensure_structure_permission(instance)
        instance.delete()

    def _touch_menu_metadata(self, menu, ordered_ids):
        metadata = menu.metadata or {}
        current_ids = list(menu.piatti.values_list('id', flat=True))
        sanitized_order = [pid for pid in ordered_ids if pid in current_ids]
        missing_ids = [pid for pid in current_ids if pid not in sanitized_order]
        metadata['piatti_order'] = sanitized_order + missing_ids
        menu.metadata = metadata
        menu.save(update_fields=['metadata', 'data_modifica'])

    def _log_audit(self, menu, action, actor=None, metadata=None):
        if menu is None:
            return
        try:
            MenuAuditEvent.objects.create(menu=menu, action=action, actor=actor, metadata=metadata or {})
        except Exception:  # pragma: no cover - l'audit non deve bloccare la richiesta
            logger.warning("Impossibile salvare evento audit", exc_info=True)

    @action(detail=True, methods=['post'])
    def add_piatto(self, request, pk=None):
        menu = self.get_object()
        self._ensure_structure_permission(menu, 'can_edit_menus')

        piatto_id = request.data.get('piatto_id')
        if not piatto_id:
            return Response({'detail': 'piatto_id è obbligatorio.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            piatto = Piatto.objects.get(id=piatto_id, company=request.user.company)
        except Piatto.DoesNotExist:
            return Response({'detail': 'Piatto non trovato.'}, status=status.HTTP_404_NOT_FOUND)

        menu.piatti.add(piatto)
        ordered_ids = list(menu.metadata.get('piatti_order', [])) if menu.metadata else []
        if piatto.id not in ordered_ids:
            ordered_ids.append(piatto.id)
        self._touch_menu_metadata(menu, ordered_ids)
        serializer = self.get_serializer(menu)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def remove_piatto(self, request, pk=None):
        menu = self.get_object()
        self._ensure_structure_permission(menu)

        piatto_id = request.data.get('piatto_id')
        if not piatto_id:
            return Response({'detail': 'piatto_id è obbligatorio.'}, status=status.HTTP_400_BAD_REQUEST)

        menu.piatti.remove(piatto_id)
        ordered_ids = list(menu.metadata.get('piatti_order', [])) if menu.metadata else []
        ordered_ids = [pid for pid in ordered_ids if pid != piatto_id]
        self._touch_menu_metadata(menu, ordered_ids)
        serializer = self.get_serializer(menu)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def reorder_piatti(self, request, pk=None):
        menu = self.get_object()
        self._ensure_structure_permission(menu)

        ordered_ids = request.data.get('order')
        if not isinstance(ordered_ids, list):
            return Response({'detail': 'order deve essere una lista di ID.'}, status=status.HTTP_400_BAD_REQUEST)

        valid_ids = set(menu.piatti.values_list('id', flat=True))
        if not set(ordered_ids).issubset(valid_ids):
            return Response({'detail': 'Alcuni ID non appartengono al menu corrente.'}, status=status.HTTP_400_BAD_REQUEST)

        self._touch_menu_metadata(menu, ordered_ids)
        serializer = self.get_serializer(menu)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='generate-documents', url_name='generate-documents')
    def generate_documents(self, request, pk=None):
        """Avvia un job Celery per generare PDF/DOCX/ZIP e restituisce l'ID del job."""

        menu = self.get_object()
        self._ensure_structure_permission(menu)

        output_format = (request.data.get('format') or 'pdf').lower()
        doc_type = (request.data.get('type') or 'menu').lower()
        include_cavalieri = str(request.data.get('include_cavalieri')).lower() in {"1", "true", "yes", "on"}

        if output_format not in dict(MenuDocumentJob.FORMAT_CHOICES):
            return Response({'detail': 'Formato non supportato.'}, status=status.HTTP_400_BAD_REQUEST)
        if doc_type not in dict(MenuDocumentJob.DOC_TYPE_CHOICES):
            return Response({'detail': 'Tipo documento non supportato.'}, status=status.HTTP_400_BAD_REQUEST)

        job = MenuDocumentJob.objects.create(
            menu=menu,
            created_by=request.user,
            output_format=output_format,
            doc_type=doc_type,
            include_cavalieri=include_cavalieri,
        )
        self._log_audit(menu, 'publish', actor=request.user, metadata={'format': output_format, 'type': doc_type})
        generate_menu_documents_task.delay(str(job.id))
        serializer = MenuDocumentJobSerializer(job, context={'request': request})
        return Response(serializer.data, status=status.HTTP_202_ACCEPTED)

    @action(detail=False, methods=['get'], url_path='document-health', url_name='document-health')
    def document_health(self, request):
        """Verifica la raggiungibilità dei worker Celery per la generazione documenti."""

        info = {
            'broker_url': settings.CELERY_BROKER_URL,
            'worker_responding': False,
            'workers': [],
        }
        try:
            inspector = current_app.control.inspect(timeout=1)
            ping = inspector.ping() or {}
            info['worker_responding'] = bool(ping)
            info['workers'] = list(ping.keys()) if ping else []
        except Exception as exc:  # pragma: no cover - dipende dal broker runtime
            info['error'] = str(exc)
        return Response(info)

    @action(
        detail=False,
        methods=['get'],
        url_path='document-jobs/(?P<job_id>[^/.]+)',
        url_name='document-job',
    )
    def document_job(self, request, job_id=None):
        job = get_object_or_404(
            MenuDocumentJob.objects.select_related('menu'),
            id=job_id,
            menu__company=request.user.company,
        )
        if job.menu.struttura:
            self._ensure_structure_permission(job.menu, 'can_publish_menu')

        serializer = MenuDocumentJobSerializer(job, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['post'], url_path='validate')
    def validate_menu(self, request):
        """Valida una bozza di menu step-by-step per l'uso nel wizard guidato."""

        data = request.data or {}
        nome = (data.get('nome') or '').strip()
        data_evento = data.get('data_evento')
        turno = data.get('turno')
        struttura = data.get('struttura')
        layout_id = data.get('layout')
        piatti_ids = data.get('piatti') or []

        steps = {}

        # Step 1: informazioni di base
        base_errors = []
        if not nome:
            base_errors.append('Inserire un nome per il menu.')
        if not data_evento:
            base_errors.append('Impostare la data dell\'evento.')
        if not turno:
            base_errors.append('Selezionare un turno.')
        if not struttura:
            base_errors.append('Associare il menu a una struttura.')
        steps['base'] = {
            'label': 'Informazioni di base',
            'status': 'ok' if not base_errors else 'error',
            'errors': base_errors,
        }

        # Step 2: layout
        layout_errors = []
        if layout_id is None:
            layout_errors.append('Scegliere un layout per proseguire.')
        steps['layout'] = {
            'label': 'Layout',
            'status': 'ok' if not layout_errors else 'error',
            'errors': layout_errors,
        }

        # Step 3: piatti e copertura categorie
        piatti_qs = Piatto.objects.filter(id__in=piatti_ids, company=request.user.company)
        found_ids = set(piatti_qs.values_list('id', flat=True))
        missing_ids = [pid for pid in piatti_ids if pid not in found_ids]
        category_counts = defaultdict(int)
        for piatto in piatti_qs:
            category_counts[piatto.categoria] += 1

        required_categories = ['antipasto', 'primo', 'secondo', 'dessert']
        missing_categories = [cat for cat in required_categories if category_counts.get(cat, 0) == 0]

        piatti_errors = []
        if missing_ids:
            piatti_errors.append('Alcuni piatti non sono disponibili o appartengono a un\'altra azienda.')
        if len(piatti_ids) < 3:
            piatti_errors.append('Aggiungere almeno 3 piatti.')
        if missing_categories:
            readable_missing = ', '.join(missing_categories)
            piatti_errors.append(f'Mancano piatti per le categorie: {readable_missing}.')

        steps['piatti'] = {
            'label': 'Composizione',
            'status': 'ok' if not piatti_errors else 'error',
            'errors': piatti_errors,
            'totale_piatti': len(piatti_ids),
            'copertura_categorie': category_counts,
        }

        # Step 4: allergeni
        allergeni_missing = [
            {'id': p.id, 'nome': p.nome}
            for p in piatti_qs.prefetch_related('allergeni')
            if p.allergeni.count() == 0
        ]
        steps['allergeni'] = {
            'label': 'Allergeni',
            'status': 'ok' if not allergeni_missing else 'error',
            'errors': [],
            'missing': allergeni_missing,
        }

        can_publish = all(step['status'] == 'ok' for step in steps.values())

        return Response({'steps': steps, 'can_publish': can_publish})

    def _current_season(self, reference_date=None):
        today = reference_date or date.today()
        month = today.month
        if month in (12, 1, 2):
            return 'inverno'
        if month in (3, 4, 5):
            return 'primavera'
        if month in (6, 7, 8):
            return 'estate'
        return 'autunno'

    @action(detail=True, methods=['get'], url_path='insights', url_name='insights')
    def menu_insights(self, request, pk=None):
        """Restituisce un riepilogo di allergeni, stagionalità e squilibri del menu."""

        menu = self.get_object()

        ref_date = parse_date(request.query_params.get('reference_date'))
        current_season = self._current_season(ref_date)

        piatti_qs = menu.piatti.prefetch_related('allergeni', 'ingredienti')
        piatti = list(piatti_qs)

        allergen_counter = defaultdict(lambda: {'count': 0, 'piatti': []})
        missing_allergens = []

        for piatto in piatti:
            allergeni = list(piatto.allergeni.all())
            if not allergeni:
                missing_allergens.append({'id': piatto.id, 'nome': piatto.nome})
            for allergene in allergeni:
                entry = allergen_counter[allergene.id]
                entry['count'] += 1
                entry['piatti'].append({'id': piatto.id, 'nome': piatto.nome})

        allergen_summary = []
        allergen_lookup = {a.id: a for a in Allergene.objects.filter(id__in=allergen_counter.keys())}
        for allergene_id, data in allergen_counter.items():
            allergene = allergen_lookup.get(allergene_id)
            allergen_summary.append({
                'id': allergene_id,
                'nome': getattr(allergene, 'nome', ''),
                'codice': getattr(allergene, 'codice', ''),
                'conteggio': data['count'],
                'piatti': data['piatti'],
            })
        allergen_summary.sort(key=lambda a: a['conteggio'], reverse=True)

        high_frequency_threshold = max(2, ceil(len(piatti) * 0.5)) if piatti else 0
        high_frequency = [a for a in allergen_summary if a['conteggio'] >= high_frequency_threshold]

        seasonality_issues = []
        in_season_ingredient_counter = defaultdict(lambda: {'count': 0, 'stagionalita': ''})
        in_season_total = 0
        total_ingredients = 0

        for piatto in piatti:
            for ingrediente in piatto.ingredienti.all():
                total_ingredients += 1
                if ingrediente.stagionalita == 'annuale' or ingrediente.stagionalita == current_season:
                    in_season_total += 1
                    entry = in_season_ingredient_counter[ingrediente.id]
                    entry['count'] += 1
                    entry['stagionalita'] = ingrediente.stagionalita
                else:
                    seasonality_issues.append({
                        'piatto': {'id': piatto.id, 'nome': piatto.nome},
                        'ingrediente': {
                            'id': ingrediente.id,
                            'nome': ingrediente.nome,
                            'stagionalita': ingrediente.stagionalita,
                        },
                    })

        in_season_ratio = (in_season_total / total_ingredients) if total_ingredients else 1
        in_season_ingredients = []
        ingredient_lookup = {
            ingrediente.id: ingrediente
            for ingrediente in Ingrediente.objects.filter(id__in=in_season_ingredient_counter.keys())
        }
        for ingrediente_id, data in in_season_ingredient_counter.items():
            ingrediente = ingredient_lookup.get(ingrediente_id)
            if not ingrediente:
                continue
            in_season_ingredients.append({
                'id': ingrediente_id,
                'nome': ingrediente.nome,
                'stagionalita': data['stagionalita'],
                'conteggio': data['count'],
            })
        in_season_ingredients.sort(key=lambda item: (-item['conteggio'], item['nome']))

        category_counts = Counter([p.categoria for p in piatti])
        missing_categories = [cat for cat in ['antipasto', 'primo', 'secondo', 'dessert'] if category_counts.get(cat, 0) == 0]

        suggestions = []
        if missing_allergens:
            suggestions.append('Compilare gli allergeni per tutti i piatti prima della pubblicazione.')
        if high_frequency:
            names = ', '.join([a['nome'] or a['codice'] for a in high_frequency])
            suggestions.append(f"Allergeni ricorrenti: {names}. Evidenziare in menu e valutare alternative.")
        if seasonality_issues:
            suggestions.append('Alcuni ingredienti risultano fuori stagione rispetto alla data selezionata.')
        if missing_categories:
            readable_missing = ', '.join(missing_categories)
            suggestions.append(f"Coprire le categorie mancanti: {readable_missing}.")

        payload = {
            'allergeni': {
                'summary': allergen_summary,
                'missing_allergeni': missing_allergens,
                'high_frequency': high_frequency,
            },
            'stagionalita': {
                'stagione_corrente': current_season,
                'fuori_stagione': seasonality_issues,
                'in_season_ratio': round(in_season_ratio, 2),
                'ingredienti_stagionali': in_season_ingredients[:6],
            },
            'categorie': {
                'copertura': dict(category_counts),
                'mancanti': missing_categories,
            },
            'suggestions': suggestions,
        }

        # Calcolo Food Cost Menu (Teorico)
        total_menu_cost = sum([p.calculate_food_cost() for p in piatti])
        total_menu_revenue = sum([float(p.prezzo or 0) for p in piatti])
        menu_margin_percent = 0
        if total_menu_revenue > 0:
            menu_margin_percent = ((total_menu_revenue - total_menu_cost) / total_menu_revenue) * 100

        payload['finanza'] = {
            'food_cost_totale': round(total_menu_cost, 2),
            'ricavo_teorico': round(total_menu_revenue, 2),
            'margine_percentuale': round(menu_margin_percent, 2),
            'piatti_critici': [
                {'id': p.id, 'nome': p.nome, 'cost_percent': round(p.food_cost_percentage, 1)}
                for p in piatti if p.food_cost_percentage > 35 # Soglia di default 35%
            ]
        }

        if payload['finanza']['piatti_critici']:
            payload['suggestions'].append(f"Attenzione: {len(payload['finanza']['piatti_critici'])} piatti superano la soglia di food cost consigliata (35%).")

        return Response(payload)

    @action(detail=True, methods=['get'], url_path='versions', url_name='versions')
    def list_versions(self, request, pk=None):
        menu = self.get_object()
        self._ensure_structure_permission(menu)

        serializer = MenuVersionSerializer(menu.versioni.all(), many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='audit', url_name='audit')
    def audit_trail(self, request, pk=None):
        menu = self.get_object()
        self._ensure_structure_permission(menu)

        events = menu.audit_events.all()
        page = self.paginate_queryset(events)
        if page is not None:
            serializer = MenuAuditEventSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = MenuAuditEventSerializer(events, many=True)
        return Response(serializer.data)

    @action(
        detail=True,
        methods=['get'],
        url_path='versions/(?P<version_id>[^/.]+)/diff',
        url_name='version-diff',
    )
    def version_diff(self, request, pk=None, version_id=None):
        menu = self.get_object()
        self._ensure_structure_permission(menu)

        version = get_object_or_404(menu.versioni, pk=version_id)
        diff = self._build_version_diff(menu, version.payload)
        return Response(diff)

    @action(
        detail=True,
        methods=['post'],
        url_path='versions/(?P<version_id>[^/.]+)/restore',
        url_name='restore-version',
    )
    def restore_version(self, request, pk=None, version_id=None):
        menu = self.get_object()
        self._ensure_structure_permission(menu)

        version = get_object_or_404(menu.versioni, pk=version_id)
        self._apply_snapshot(menu, version.payload)
        self._log_audit(menu, 'restore', actor=request.user, metadata={'version': version_id})
        serializer = self.get_serializer(menu)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='versions/snapshot', url_name='snapshot')
    def create_snapshot(self, request, pk=None):
        menu = self.get_object()
        self._ensure_structure_permission(menu)

        snapshot = menu.snapshot()
        version = MenuVersion.objects.create(menu=menu, creato_da=request.user, payload=snapshot)
        self._log_audit(menu, 'snapshot', actor=request.user, metadata={'version': str(version.id)})
        serializer = MenuVersionSerializer(version)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def _apply_snapshot(self, menu, payload):
        menu.nome = payload.get('nome', menu.nome)
        data_evento = payload.get('data_evento')
        menu.data_evento = parse_date(data_evento) if data_evento else None
        menu.turno = payload.get('turno') or menu.turno
        menu.ospiti_target = payload.get('ospiti_target', '')
        menu.note = payload.get('note', '')
        menu.layout_id = payload.get('layout')
        menu.cavaliere_template_id = payload.get('cavaliere_template')
        menu.metadata = payload.get('metadata') or {}
        menu.save()

        piatti_payload = payload.get('piatti') or []
        valid_piatti_ids = list(
            Piatto.objects.filter(id__in=[p.get('id') for p in piatti_payload], company=menu.company)
            .values_list('id', flat=True)
        )
        menu.piatti.set(valid_piatti_ids)
        ordered_ids = [pid for pid in (menu.metadata.get('piatti_order', []) or []) if pid in valid_piatti_ids]
        if ordered_ids:
            menu.metadata['piatti_order'] = ordered_ids
            menu.save(update_fields=['metadata'])

    def _build_version_diff(self, menu, version_payload):
        current_snapshot = menu.snapshot()

        def _normalize_date(value):
            return value or None

        changed_fields = []
        tracked_fields = ['nome', 'data_evento', 'turno', 'ospiti_target', 'note', 'layout', 'cavaliere_template']
        for field in tracked_fields:
            current_value = current_snapshot.get(field)
            version_value = version_payload.get(field)
            if field == 'data_evento':
                current_value = _normalize_date(current_value)
                version_value = _normalize_date(version_value)
            if current_value != version_value:
                changed_fields.append({
                    'field': field,
                    'current': current_value,
                    'version': version_value,
                })

        current_piatti = current_snapshot.get('piatti', [])
        version_piatti = version_payload.get('piatti', [])

        def _piatto_lookup(items):
            return {item.get('id'): {
                'id': item.get('id'),
                'nome': item.get('nome'),
                'categoria': item.get('categoria'),
            } for item in items if item.get('id')}

        current_lookup = _piatto_lookup(current_piatti)
        version_lookup = _piatto_lookup(version_piatti)

        current_ids = [p.get('id') for p in current_piatti if p.get('id')]
        version_ids = [p.get('id') for p in version_piatti if p.get('id')]

        added_ids = [pid for pid in current_ids if pid not in version_ids]
        removed_ids = [pid for pid in version_ids if pid not in current_ids]

        shared_current_order = [pid for pid in current_ids if pid in version_ids]
        shared_version_order = [pid for pid in version_ids if pid in current_ids]
        order_changed = shared_current_order != shared_version_order

        return {
            'changed_fields': changed_fields,
            'piatti': {
                'added': [current_lookup.get(pid) for pid in added_ids],
                'removed': [version_lookup.get(pid) for pid in removed_ids],
                'order_changed': order_changed,
                'current_order': shared_current_order,
                'version_order': shared_version_order,
            },
        }


class ExecutiveDashboardViewSet(viewsets.ViewSet):
    """Dashboard per proprietari ed executive per monitorare le attività di tutte le strutture."""

    permission_classes = [CanAccessMenuGenerator]

    def list(self, request):
        user = request.user
        is_superuser = _is_effectively_superuser(user)
        is_owner = user.role == "owner"

        if not (is_superuser or is_owner):
            raise PermissionDenied("Accesso riservato a Proprietari e Super Admin.")

        # Filtro società
        company_id = request.query_params.get('company')
        if is_superuser:
            if company_id:
                company = get_object_or_404(Company, id=company_id)
            else:
                company = Company.objects.first()
        else:
            company = user.company

        if not company:
            return Response({"detail": "Nessuna società associata."}, status=400)

        # Strutture della società
        structures = Structure.objects.filter(company=company, is_active=True)

        # Statistiche globali (ultimo mese)
        last_month = timezone.now() - timezone.timedelta(days=30)

        total_menus = Menu.objects.filter(company=company, data_creazione__gte=last_month).count()
        total_published = Menu.objects.filter(company=company, is_published=True, published_at__gte=last_month).count()
        total_exports = MenuDocumentJob.objects.filter(
            menu__company=company,
            status=MenuDocumentJob.STATUS_SUCCESS,
            created_at__gte=last_month
        ).count()

        # Piatti più usati (Top 5)
        top_piatti = Piatto.objects.filter(company=company, menu__data_creazione__gte=last_month) \
            .annotate(usage_count=models.Count('menu')) \
            .order_by('-usage_count')[:5]

        # Dati per struttura (Live Tiles)
        structure_stats = []
        for struct in structures:
            recent_menu = Menu.objects.filter(struttura=struct).order_by('-data_creazione').first()
            struct_total_menus = Menu.objects.filter(struttura=struct).count()

            structure_stats.append({
                "id": struct.id,
                "name": struct.name,
                "total_menus": struct_total_menus,
                "last_activity": recent_menu.data_creazione if recent_menu else None,
                "last_menu_name": recent_menu.nome if recent_menu else None,
                "is_active": struct.is_active,
            })

        return Response({
            "company_name": company.name,
            "stats": {
                "total_menus_30d": total_menus,
                "total_published_30d": total_published,
                "total_exports_30d": total_exports,
            },
            "top_piatti": [
                {"id": p.id, "nome": p.nome, "usage": p.usage_count} for p in top_piatti
            ],
            "structures": structure_stats
        })


class PublicPiattoDetailView(DetailView):
    """Vista pubblica per visualizzare i dettagli di un piatto tramite QR Code."""
    model = Piatto
    template_name = "menu_generator/public_piatto.html"
    slug_field = "uuid"
    slug_url_kwarg = "piatto_uuid"
    context_object_name = "piatto"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['allergeni'] = self.object.allergeni.all()
        context['ingredienti'] = self.object.ingredienti.all()
        return context
