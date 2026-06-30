from collections import defaultdict
from datetime import datetime

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, F, Q, Sum
from django.utils import timezone
from django.views.generic import TemplateView
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from clients.models import Company
from resort.models import Resort
from core.models import InAppGuideAsset

from . import models, serializers


def build_economato_guide(user):
    role_labels = dict(User.ROLE_CHOICES)
    role = getattr(user, 'role', None)
    role_label = role_labels.get(role, 'Operatore')

    common_steps = [
        {
            "key": "economato-overview",
            "title": "Panoramica immediata",
            "description": "Il riquadro iniziale riassume stock, richieste e budget attivi. Usa questo spazio come punto di partenza rapido per la giornata.",
            "selector": "#economato-hero",
        },
        {
            "key": "economato-scope",
            "title": "Filtra il perimetro di lavoro",
            "description": "Seleziona società e resort per restringere i dati alle strutture su cui hai responsabilità operative.",
            "selector": "#economato-scope-selector",
        },
        {
            "key": "economato-kpi",
            "title": "Indicatori critici",
            "description": "Monitora articoli sotto scorta, andamento richieste e budget impegnato nel mese in un'unica griglia responsive.",
            "selector": "#economato-kpi-grid",
        },
        {
            "key": "economato-workflow",
            "title": "Workflow richieste",
            "description": "Accedi alla tab Richieste per consultare il board kanban e seguire lo stato delle lavorazioni in tempo reale.",
            "selector": "#economato-tab-requests",
        },
    ]

    manage_step = {
        "key": "economato-new-request",
        "title": "Nuove richieste",
        "description": "Avvia una richiesta dall'azione dedicata: la procedura guidata verifica budget, centri di costo e fornitori.",
        "selector": "#economato-new-request",
    }

    approval_step = {
        "key": "economato-approvals",
        "title": "Approvazioni rapide",
        "description": "Dal menu delle azioni rapidi puoi aprire timeline e commenti per approvare o richiedere integrazioni alle strutture.",
        "selector": "#economato-header-actions",
    }

    insight_step = {
        "key": "economato-insight",
        "title": "Insight per decision maker",
        "description": "Confronta budget e trend mensili per validare le azioni di spesa e prevenire criticità.",
        "selector": "#economato-highlights",
    }

    role_steps = {
        User.SUPERADMIN: [*common_steps, manage_step, approval_step, insight_step],
        User.ECONOMO: [*common_steps, manage_step, approval_step],
        User.CAPO_ECONOMO: [*common_steps, approval_step, manage_step],
        User.DIRECTOR: [*common_steps, insight_step, approval_step],
        User.OWNER: [*common_steps, insight_step, manage_step],
    }

    assets = InAppGuideAsset.objects.active().filter(guide_key='economato')
    assets_by_step = defaultdict(list)
    for asset in assets:
        assets_by_step[asset.step_key].append(asset.as_payload())

    def enrich(step_list):
        enriched = []
        for index, step in enumerate(step_list):
            base = dict(step)
            step_key = base.get('key') or base.get('selector') or f'economato-step-{index + 1}'
            base['key'] = step_key
            if assets_by_step.get(step_key):
                base['resources'] = assets_by_step[step_key]
            else:
                base.pop('resources', None)
            enriched.append(base)
        return enriched

    return {
        "key": "economato",
        "title": "Guida rapida Economato",
        "description": f"Scopri le funzioni fondamentali pensate per il ruolo {role_label.lower()}.",
        "menu_label": "Guida Economato",
        "cta_label": "Inizia tour",
        "roles": {
            **{role_name: enrich(steps_list) for role_name, steps_list in role_steps.items()},
            "default": enrich([*common_steps, manage_step]),
        },
        "role_labels": role_labels,
    }


class EconomatoScope:
    """Utility per calcolare i permessi di visibilità e modifica nell'economato."""

    def __init__(self, user):
        self.user = user
        self.role = getattr(user, 'role', None)
        self._allowed_companies = None
        self._allowed_resorts = None
        self.current_company_id = None
        self.current_resort_id = None

    # --- Proprietà base ---
    @property
    def is_global(self):
        return bool(self.user.is_superuser or self.role == User.SUPERADMIN)

    @property
    def has_company_wide_scope(self):
        return self.is_global or self.role in {User.OWNER, User.CAPO_ECONOMO}

    @property
    def is_resort_manager(self):
        return self.role in {User.ECONOMO, User.DIRECTOR}

    @property
    def can_manage(self):
        return self.is_global or self.role in {User.OWNER, User.CAPO_ECONOMO, User.ECONOMO}

    @property
    def is_read_only(self):
        return self.role == User.DIRECTOR and not self.is_global

    # --- Scope calculation ---
    def allowed_company_ids(self):
        if self.is_global:
            return None
        if self._allowed_companies is None:
            if self.user.company_id:
                self._allowed_companies = {self.user.company_id}
            else:
                self._allowed_companies = set()
        return self._allowed_companies

    def allowed_resort_ids(self, company_ids=None):
        if self.is_global:
            return None
        if self._allowed_resorts is not None:
            return self._allowed_resorts

        if self.has_company_wide_scope and self.user.company_id:
            qs = Resort.objects.filter(company_id=self.user.company_id)
            if company_ids:
                qs = qs.filter(company_id__in=company_ids)
            self._allowed_resorts = set(qs.values_list('id', flat=True))
        elif self.user.resort_id:
            self._allowed_resorts = {self.user.resort_id}
        else:
            self._allowed_resorts = set()
        return self._allowed_resorts

    def has_company_access(self, company_id):
        allowed = self.allowed_company_ids()
        if allowed is None:
            return True
        return company_id in allowed

    def has_resort_access(self, resort_id):
        if resort_id is None:
            return True
        allowed = self.allowed_resort_ids()
        if allowed is None:
            return True
        return resort_id in allowed

    def _normalize_id(self, value):
        if value is None or value == '':
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            raise PermissionDenied('Identificativo non valido fornito per la selezione.')

    def _resolve_company_ids(self, requested_company_id):
        requested_company_id = self._normalize_id(requested_company_id)
        allowed = self.allowed_company_ids()
        if self.is_global:
            if requested_company_id:
                self.current_company_id = requested_company_id
                return [requested_company_id]
            self.current_company_id = requested_company_id
            return None
        if allowed is None:
            return None
        if not allowed:
            self.current_company_id = None
            return []
        if requested_company_id:
            if requested_company_id not in allowed:
                raise PermissionDenied('Non hai accesso alla società selezionata.')
            self.current_company_id = requested_company_id
            return [requested_company_id]
        if len(allowed) == 1:
            self.current_company_id = next(iter(allowed))
        else:
            self.current_company_id = self.user.company_id if self.user.company_id in allowed else None
        return list(allowed)

    def _resolve_resort_ids(self, requested_resort_id, company_ids, allow_missing_resort):
        requested_resort_id = self._normalize_id(requested_resort_id)
        allowed = self.allowed_resort_ids(company_ids)
        if allowed is None:
            if requested_resort_id:
                self.current_resort_id = requested_resort_id
                return [requested_resort_id]
            self.current_resort_id = requested_resort_id
            return None
        if not allowed:
            self.current_resort_id = None
            return []
        if requested_resort_id:
            if requested_resort_id not in allowed:
                raise PermissionDenied('Non hai accesso al resort selezionato.')
            self.current_resort_id = requested_resort_id
            return [requested_resort_id]
        if len(allowed) == 1:
            self.current_resort_id = next(iter(allowed))
            return list(allowed)
        if self.user.resort_id and self.user.resort_id in allowed:
            self.current_resort_id = self.user.resort_id
        else:
            self.current_resort_id = None
        return list(allowed)

    def apply_filters(
        self,
        queryset,
        requested_company_id=None,
        requested_resort_id=None,
        company_lookup='company',
        resort_lookup='resort',
        allow_missing_resort=False,
    ):
        company_ids = self._resolve_company_ids(requested_company_id)
        resort_ids = self._resolve_resort_ids(requested_resort_id, company_ids, allow_missing_resort)

        if company_lookup and company_ids is not None:
            if not company_ids:
                return queryset.none()
            queryset = queryset.filter(**{f'{company_lookup}__in': company_ids})
        if resort_lookup:
            if resort_ids is None:
                return queryset
            if not resort_ids:
                if allow_missing_resort:
                    return queryset.filter(Q(**{f'{resort_lookup}__isnull': True}))
                return queryset.none()
            if allow_missing_resort:
                queryset = queryset.filter(
                    Q(**{f'{resort_lookup}__in': resort_ids}) | Q(**{f'{resort_lookup}__isnull': True})
                )
            else:
                queryset = queryset.filter(**{f'{resort_lookup}__in': resort_ids})
        return queryset

    def describe_scope(self):
        return {
            'is_global': self.is_global,
            'has_company_wide_scope': self.has_company_wide_scope,
            'can_manage': self.can_manage,
            'is_read_only': self.is_read_only,
            'current_company_id': self.current_company_id,
            'current_resort_id': self.current_resort_id,
        }

    def ensure_company_resort(self, company_id, resort_id=None):
        if company_id and not self.has_company_access(company_id):
            raise PermissionDenied('Non hai accesso alla società selezionata.')
        if resort_id and not self.has_resort_access(resort_id):
            raise PermissionDenied('Non hai accesso al resort selezionato.')


class EconomatoPermission(permissions.BasePermission):
    message = 'Non hai i permessi per accedere alla sezione Economato.'

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        role = getattr(request.user, 'role', None)
        return role in {
            User.SUPERADMIN,
            User.OWNER,
            User.CAPO_ECONOMO,
            User.ECONOMO,
            User.DIRECTOR,
        }

    def has_object_permission(self, request, view, obj):
        scope = getattr(view, 'get_scope', None)
        if callable(scope):
            scope = scope()
            if isinstance(obj, models.EconomatoRequest):
                return scope.has_company_access(obj.company_id) and scope.has_resort_access(obj.resort_id)
            if isinstance(obj, models.EconomatoItem):
                return scope.has_company_access(obj.company_id) and scope.has_resort_access(getattr(obj, 'resort_id', None))
        return True


class EconomatoScopedViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated, EconomatoPermission]
    company_lookup = 'company'
    resort_lookup = 'resort'
    allow_missing_resort = False

    def get_scope(self):
        if not hasattr(self, '_economato_scope'):
            self._economato_scope = EconomatoScope(self.request.user)
        return self._economato_scope

    def filter_queryset(self, queryset):
        scope = self.get_scope()
        return scope.apply_filters(
            super().filter_queryset(queryset),
            requested_company_id=self.request.query_params.get('company'),
            requested_resort_id=self.request.query_params.get('resort'),
            company_lookup=self.company_lookup,
            resort_lookup=self.resort_lookup,
            allow_missing_resort=self.allow_missing_resort,
        )

    def ensure_can_modify(self):
        scope = self.get_scope()
        if scope.is_read_only:
            raise PermissionDenied('Il tuo profilo può solo visualizzare i dati dell\'economato.')
        if not scope.can_manage:
            raise PermissionDenied('Non hai i permessi per modificare i dati dell\'economato.')


class EconomatoCategoryViewSet(EconomatoScopedViewSet):
    queryset = models.EconomatoCategory.objects.all().select_related('company')
    serializer_class = serializers.EconomatoCategorySerializer
    resort_lookup = None

    def perform_create(self, serializer):
        self.ensure_can_modify()
        company = serializer.validated_data['company']
        self.get_scope().ensure_company_resort(company_id=company.id)
        serializer.save()

    def perform_update(self, serializer):
        self.ensure_can_modify()
        company = serializer.validated_data.get('company', serializer.instance.company)
        self.get_scope().ensure_company_resort(company_id=company.id)
        serializer.save()

    def perform_destroy(self, instance):
        self.ensure_can_modify()
        self.get_scope().ensure_company_resort(company_id=instance.company_id)
        super().perform_destroy(instance)


class EconomatoCostCenterViewSet(EconomatoScopedViewSet):
    queryset = models.EconomatoCostCenter.objects.select_related('company')
    serializer_class = serializers.EconomatoCostCenterSerializer
    resort_lookup = None

    def perform_create(self, serializer):
        self.ensure_can_modify()
        self.get_scope().ensure_company_resort(company_id=serializer.validated_data['company'].id)
        serializer.save()

    def perform_update(self, serializer):
        self.ensure_can_modify()
        company = serializer.validated_data.get('company', serializer.instance.company)
        self.get_scope().ensure_company_resort(company_id=company.id)
        serializer.save()

    def perform_destroy(self, instance):
        self.ensure_can_modify()
        self.get_scope().ensure_company_resort(company_id=instance.company_id)
        super().perform_destroy(instance)


class EconomatoItemViewSet(EconomatoScopedViewSet):
    queryset = models.EconomatoItem.objects.select_related('company', 'resort', 'category', 'supplier')
    serializer_class = serializers.EconomatoItemSerializer
    allow_missing_resort = True

    def perform_create(self, serializer):
        self.ensure_can_modify()
        company = serializer.validated_data['company']
        resort = serializer.validated_data.get('resort')
        self.get_scope().ensure_company_resort(company.id, resort.id if resort else None)
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        self.ensure_can_modify()
        company = serializer.validated_data.get('company', serializer.instance.company)
        resort = serializer.validated_data.get('resort', serializer.instance.resort)
        self.get_scope().ensure_company_resort(company.id, resort.id if resort else None)
        serializer.save()

    def perform_destroy(self, instance):
        self.ensure_can_modify()
        self.get_scope().ensure_company_resort(instance.company_id, instance.resort_id)
        super().perform_destroy(instance)


class EconomatoStockLevelViewSet(EconomatoScopedViewSet):
    queryset = models.EconomatoStockLevel.objects.select_related('item', 'resort', 'item__company')
    serializer_class = serializers.EconomatoStockLevelSerializer
    company_lookup = 'item__company'

    def perform_update(self, serializer):
        self.ensure_can_modify()
        resort = serializer.validated_data.get('resort', serializer.instance.resort)
        self.get_scope().ensure_company_resort(serializer.instance.item.company_id, resort.id if resort else None)
        serializer.save(updated_by=self.request.user)

    def perform_destroy(self, instance):
        self.ensure_can_modify()
        self.get_scope().ensure_company_resort(instance.item.company_id, instance.resort_id)
        super().perform_destroy(instance)

    def perform_create(self, serializer):
        self.ensure_can_modify()
        item = serializer.validated_data['item']
        resort = serializer.validated_data['resort']
        self.get_scope().ensure_company_resort(item.company_id, resort.id if resort else None)
        serializer.save(updated_by=self.request.user)


class EconomatoRequestViewSet(EconomatoScopedViewSet):
    queryset = models.EconomatoRequest.objects.select_related(
        'company', 'resort', 'requested_by', 'approved_by', 'cost_center'
    ).prefetch_related('items')
    serializer_class = serializers.EconomatoRequestSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        status_param = self.request.query_params.get('status')
        if status_param:
            qs = qs.filter(status=status_param)
        priority_param = self.request.query_params.get('priority')
        if priority_param:
            qs = qs.filter(priority=priority_param)
        return qs

    def perform_create(self, serializer):
        self.ensure_can_modify()
        company = serializer.validated_data['company']
        resort = serializer.validated_data['resort']
        self.get_scope().ensure_company_resort(company.id, resort.id)
        instance = serializer.save(requested_by=self.request.user)
        models.EconomatoTimelineEvent.objects.create(
            request=instance,
            created_by=self.request.user,
            verb='Richiesta creata',
            payload={'status': instance.status, 'priority': instance.priority},
        )

    def perform_update(self, serializer):
        self.ensure_can_modify()
        company = serializer.validated_data.get('company', serializer.instance.company)
        resort = serializer.validated_data.get('resort', serializer.instance.resort)
        self.get_scope().ensure_company_resort(company.id, resort.id)
        previous_status = serializer.instance.status
        instance = serializer.save()
        if previous_status != instance.status:
            models.EconomatoTimelineEvent.objects.create(
                request=instance,
                created_by=self.request.user,
                verb='Aggiornamento stato',
                payload={'from': previous_status, 'to': instance.status},
            )

    @action(detail=True, methods=['post'])
    def change_status(self, request, pk=None):
        scope = self.get_scope()
        if scope.is_read_only:
            raise PermissionDenied('Non hai i permessi per modificare lo stato della richiesta.')
        instance = self.get_object()
        new_status = request.data.get('status')
        valid_statuses = dict(models.EconomatoRequest.STATUS_CHOICES).keys()
        if new_status not in valid_statuses:
            return Response({'detail': 'Stato non valido.'}, status=status.HTTP_400_BAD_REQUEST)
        if new_status == models.EconomatoRequest.STATUS_APPROVED and not scope.can_manage:
            raise PermissionDenied('Solo i profili autorizzati possono approvare le richieste.')
        previous_status = instance.status
        instance.status = new_status
        if new_status == models.EconomatoRequest.STATUS_APPROVED:
            instance.approved_by = request.user
        instance.save(update_fields=['status', 'approved_by', 'updated_at'])
        models.EconomatoTimelineEvent.objects.create(
            request=instance,
            created_by=request.user,
            verb='Cambio stato manuale',
            payload={'from': previous_status, 'to': new_status},
        )
        return Response(self.get_serializer(instance).data)


class EconomatoTimelineView(APIView):
    permission_classes = [permissions.IsAuthenticated, EconomatoPermission]

    def get(self, request, request_id):
        scope = EconomatoScope(request.user)
        timeline_qs = models.EconomatoTimelineEvent.objects.filter(request_id=request_id).select_related('request', 'created_by')
        timeline_qs = scope.apply_filters(
            timeline_qs,
            requested_company_id=request.query_params.get('company'),
            requested_resort_id=request.query_params.get('resort'),
            company_lookup='request__company',
            resort_lookup='request__resort',
        )
        serializer = serializers.EconomatoTimelineEventSerializer(timeline_qs, many=True)
        return Response(serializer.data)


class EconomatoOverviewAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, EconomatoPermission]

    def get(self, request):
        scope = EconomatoScope(request.user)
        requested_company = request.query_params.get('company')
        requested_resort = request.query_params.get('resort')

        item_qs = scope.apply_filters(
            models.EconomatoItem.objects.select_related('company', 'resort', 'category'),
            requested_company_id=requested_company,
            requested_resort_id=requested_resort,
            allow_missing_resort=True,
        )
        stock_qs = scope.apply_filters(
            models.EconomatoStockLevel.objects.select_related('item', 'item__company', 'resort'),
            requested_company_id=requested_company,
            requested_resort_id=requested_resort,
            company_lookup='item__company',
        )
        request_qs = scope.apply_filters(
            models.EconomatoRequest.objects.select_related('company', 'resort', 'requested_by', 'approved_by', 'cost_center'),
            requested_company_id=requested_company,
            requested_resort_id=requested_resort,
        )

        stats = {
            'total_items': float(item_qs.count()),
            'low_stock_items': float(
                stock_qs.annotate(available=F('quantity') - F('reserved_quantity'))
                .filter(available__lte=F('item__reorder_point'))
                .count()
            ),
            'active_requests': float(
                request_qs.filter(status__in=[
                    models.EconomatoRequest.STATUS_PENDING,
                    models.EconomatoRequest.STATUS_APPROVED,
                ]).count()
            ),
            'critical_requests': float(
                request_qs.filter(priority=models.EconomatoRequest.PRIORITY_CRITICAL).count()
            ),
        }

        month_start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        stats['monthly_estimated_cost'] = float(
            request_qs.filter(created_at__gte=month_start).aggregate(total=Sum('total_estimated_cost'))['total'] or 0
        )

        low_stock = (
            stock_qs.annotate(available=F('quantity') - F('reserved_quantity'))
            .filter(available__lte=F('item__reorder_point'))
            .order_by('available')[:10]
        )

        requests_by_status = defaultdict(int)
        for row in request_qs.values('status').annotate(total=Count('id')):
            requests_by_status[row['status']] = row['total']

        recent_requests = request_qs.order_by('-created_at')[:6]

        available_companies = []
        allowed_companies = scope.allowed_company_ids()
        if scope.is_global:
            companies_qs = Company.objects.all()
            if requested_company:
                companies_qs = companies_qs.filter(id=int(requested_company))
            available_companies = list(companies_qs.values('id', 'name'))
        elif allowed_companies:
            available_companies = list(
                Company.objects.filter(id__in=allowed_companies).values('id', 'name')
            )

        available_resorts = []
        allowed_resorts = scope.allowed_resort_ids()
        if scope.is_global:
            resorts_qs = Resort.objects.all()
            if requested_company:
                resorts_qs = resorts_qs.filter(company_id=int(requested_company))
            available_resorts = list(resorts_qs.values('id', 'name', 'company_id'))
        elif allowed_resorts:
            resorts_qs = Resort.objects.filter(id__in=allowed_resorts)
            if requested_company:
                resorts_qs = resorts_qs.filter(company_id=int(requested_company))
            available_resorts = list(resorts_qs.values('id', 'name', 'company_id'))

        payload = {
            'stats': stats,
            'low_stock_items': low_stock,
            'requests_by_status': dict(requests_by_status),
            'recent_requests': recent_requests,
            'available_companies': available_companies,
            'available_resorts': available_resorts,
            'scope': scope.describe_scope(),
        }
        serializer = serializers.EconomatoOverviewSerializer(payload)
        return Response(serializer.data)


class EconomatoReactAppView(LoginRequiredMixin, TemplateView):
    template_name = 'economato/react_root.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['in_app_guide'] = build_economato_guide(self.request.user)
        return context
