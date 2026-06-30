from collections import defaultdict
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, DecimalField, F, Q, Sum
from django.db.models.functions import Coalesce, ExtractMonth
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone

from accounts.models import User
from clients.models import Company
from core.decorators import role_required
from core.utils import themed_render
from core.models import InAppGuideAsset
from economato.models import EconomatoRequest
from purchase_orders.models import Budget, PurchaseOrderItem
from resort.models import Resort

from .forms import (
    FinancialDashboardFilterForm,
    FinancialLineItemFormSet,
    FinancialPeriodForm,
    FinancialSnapshotFilterForm,
    FinancialSnapshotForm,
)
from .models import FinancialImportBatch, FinancialLineItem, FinancialPeriod, FinancialSnapshot

ALLOWED_ROLES = [
    User.SUPERADMIN,
    User.OWNER,
    User.DIRECTOR,
    User.ADMINISTRATIVE,
]


def build_financials_guide(user):
    role_labels = dict(User.ROLE_CHOICES)
    role = getattr(user, 'role', None)
    role_label = role_labels.get(role, 'Decision maker')

    common_steps = [
        {
            "key": "financials-hero",
            "title": "Cruscotto sintetico",
            "description": "La hero riassume pulsanti chiave e contestualizza la chiusura annuale: avvia da qui snapshot e nuove analisi.",
            "selector": "#financials-dashboard-hero",
        },
        {
            "key": "financials-filter",
            "title": "Filtri dinamici",
            "description": "Limita la vista scegliendo società, struttura e anno di riferimento: la dashboard si aggiorna in tempo reale.",
            "selector": "#financials-filter",
        },
        {
            "key": "financials-kpi",
            "title": "Indicatori principali",
            "description": "I KPI rispondono in modo responsive: scorri per ricavi, costi e margini con badge di varianza YoY.",
            "selector": "#financials-kpi-grid",
        },
        {
            "key": "financials-visual",
            "title": "Analisi visive",
            "description": "Grafici e tabelle evidenziano trend mensili e categorie prioritarie; esporta i dati dai pulsanti snapshot.",
            "selector": "#financials-chart-area",
        },
    ]

    operations_step = {
        "key": "financials-operations",
        "title": "Controllo operativo",
        "description": "Verifica ordini, economato e budget allocato per presidiare la spesa con un colpo d'occhio.",
        "selector": "#financials-operational",
    }

    strategy_step = {
        "key": "financials-strategy",
        "title": "Alert strategici",
        "description": "Opportunità e warning guidano le priorità di azione con indicazioni sulla varianza e sulle leve di crescita.",
        "selector": "#financials-strategy",
    }

    role_steps = {
        User.SUPERADMIN: [*common_steps, strategy_step, operations_step],
        User.ADMINISTRATIVE: [*common_steps, operations_step, strategy_step],
        User.DIRECTOR: [*common_steps, strategy_step, operations_step],
        User.OWNER: [*common_steps, strategy_step, operations_step],
    }

    assets = InAppGuideAsset.objects.active().filter(guide_key='financials')
    assets_by_step = defaultdict(list)
    for asset in assets:
        assets_by_step[asset.step_key].append(asset.as_payload())

    def enrich(step_list):
        enriched = []
        for index, step in enumerate(step_list):
            base = dict(step)
            step_key = base.get('key') or base.get('selector') or f'financials-step-{index + 1}'
            base['key'] = step_key
            if assets_by_step.get(step_key):
                base['resources'] = assets_by_step[step_key]
            else:
                base.pop('resources', None)
            enriched.append(base)
        return enriched

    return {
        "key": "financials",
        "title": "Guida rapida Controllo Amministrativo",
        "description": f"Orientati tra i moduli della dashboard pensata per il ruolo {role_label.lower()}.",
        "menu_label": "Guida Controllo Amm.",
        "cta_label": "Inizia tour",
        "roles": {
            **{role_name: enrich(steps_list) for role_name, steps_list in role_steps.items()},
            "default": enrich([*common_steps, operations_step]),
        },
        "role_labels": role_labels,
    }


def _get_accessible_companies(user):
    if user.is_superuser or getattr(user, 'role', None) == User.SUPERADMIN:
        return Company.objects.all()
    if getattr(user, 'role', None) in {User.OWNER, User.ADMINISTRATIVE, User.DIRECTOR} and user.company_id:
        return Company.objects.filter(pk=user.company_id)
    return Company.objects.none()


def _get_accessible_resorts(user, company=None):
    if user.is_superuser or getattr(user, 'role', None) == User.SUPERADMIN:
        qs = Resort.objects.all()
    elif user.company_id:
        qs = Resort.objects.filter(company=user.company)
    else:
        qs = Resort.objects.none()
    if company:
        qs = qs.filter(company=company)
    return qs


def _coalesce_decimal(value):
    if value is None:
        return Decimal('0')
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _percentage(part, whole):
    part = _coalesce_decimal(part)
    whole = _coalesce_decimal(whole)
    if not whole:
        return Decimal('0')
    return (part / whole) * Decimal('100')


def _growth(current, previous):
    current = _coalesce_decimal(current)
    previous = _coalesce_decimal(previous)
    delta = current - previous
    percentage = _percentage(delta, previous) if previous else Decimal('0')
    return delta, percentage


def _clamp_percentage(value, minimum=Decimal('0'), maximum=Decimal('100')):
    value = _coalesce_decimal(value)
    if value < minimum:
        return minimum
    if value > maximum:
        return maximum
    return value


def _aggregate_snapshot(qs, snapshot_type):
    aggregates = qs.filter(snapshot_type=snapshot_type).aggregate(
        revenue=Coalesce(Sum('total_revenue'), Decimal('0')),
        costs=Coalesce(Sum('total_costs'), Decimal('0')),
    )
    revenue = _coalesce_decimal(aggregates['revenue'])
    costs = _coalesce_decimal(aggregates['costs'])
    margin = revenue - costs
    return {
        'revenue': revenue,
        'costs': costs,
        'margin': margin,
        'margin_percentage': (margin / revenue * 100) if revenue else Decimal('0'),
    }


def _build_monthly_margin_series(qs, snapshot_type):
    monthly_data = {month: Decimal('0') for month in range(1, 13)}
    values = (
        qs.filter(snapshot_type=snapshot_type)
        .values('period__month')
        .annotate(
            revenue=Coalesce(Sum('total_revenue'), Decimal('0')),
            costs=Coalesce(Sum('total_costs'), Decimal('0')),
        )
    )
    for entry in values:
        month = entry['period__month'] or 0
        if month:
            revenue = _coalesce_decimal(entry['revenue'])
            costs = _coalesce_decimal(entry['costs'])
            monthly_data[month] = revenue - costs
    return [float(monthly_data[month]) for month in range(1, 13)]


def _build_purchase_order_series(po_items):
    annotated = (
        po_items.annotate(month=ExtractMonth('purchase_order__created_at'))
        .values('month')
        .annotate(
            total=Coalesce(
                Sum(
                    F('quantity') * F('unit_price'),
                    output_field=DecimalField(max_digits=16, decimal_places=2),
                ),
                Decimal('0'),
            )
        )
    )
    data = {month: Decimal('0') for month in range(1, 13)}
    for entry in annotated:
        month = entry['month'] or 0
        if month:
            data[month] = _coalesce_decimal(entry['total'])
    return [float(data[month]) for month in range(1, 13)]


def _build_monthly_totals(qs, snapshot_type):
    monthly_totals = {
        month: {'revenue': Decimal('0'), 'costs': Decimal('0')}
        for month in range(1, 13)
    }
    values = (
        qs.filter(snapshot_type=snapshot_type)
        .values('period__month')
        .annotate(
            revenue=Coalesce(Sum('total_revenue'), Decimal('0')),
            costs=Coalesce(Sum('total_costs'), Decimal('0')),
        )
    )
    for entry in values:
        month = entry['period__month'] or 0
        if month:
            monthly_totals[month]['revenue'] = _coalesce_decimal(entry['revenue'])
            monthly_totals[month]['costs'] = _coalesce_decimal(entry['costs'])
    return monthly_totals


def _compute_run_rate(actual_totals, monthly_totals):
    active_months = [
        month
        for month, values in monthly_totals.items()
        if values['revenue'] or values['costs']
    ]
    if not active_months:
        return {
            'revenue': actual_totals['revenue'],
            'costs': actual_totals['costs'],
            'margin': actual_totals['margin'],
            'months_recorded': 0,
            'factor': Decimal('1'),
        }
    months_recorded = len(active_months)
    factor = Decimal('12') / Decimal(months_recorded)
    projected_revenue = actual_totals['revenue'] * factor
    projected_costs = actual_totals['costs'] * factor
    projected_margin = projected_revenue - projected_costs
    return {
        'revenue': projected_revenue,
        'costs': projected_costs,
        'margin': projected_margin,
        'months_recorded': months_recorded,
        'factor': factor,
    }


def _score_from_ratio(value, upper_bound=Decimal('130')):
    value = _coalesce_decimal(value)
    if value <= 0:
        return Decimal('0')
    capped = value if value < upper_bound else upper_bound
    return _clamp_percentage((capped / upper_bound) * Decimal('100'))


def _score_from_cost_efficiency(cost_efficiency):
    cost_efficiency = _coalesce_decimal(cost_efficiency)
    if cost_efficiency <= Decimal('100'):
        improvement = Decimal('100') - cost_efficiency
        base = Decimal('100') + (improvement if improvement < Decimal('15') else Decimal('15'))
    else:
        penalty = cost_efficiency - Decimal('100')
        base = Decimal('100') - (penalty if penalty < Decimal('40') else Decimal('40'))
    return _clamp_percentage((base / Decimal('115')) * Decimal('100'))


def _compute_health_metadata(
    revenue_attainment,
    cost_efficiency,
    margin_coverage,
    import_stats_map,
    budget_gap_ratio,
):
    revenue_score = _score_from_ratio(revenue_attainment, Decimal('135'))
    margin_score = _score_from_ratio(margin_coverage, Decimal('140'))
    cost_score = _score_from_cost_efficiency(cost_efficiency)

    score = (
        revenue_score * Decimal('0.35')
        + margin_score * Decimal('0.4')
        + cost_score * Decimal('0.25')
    )

    if import_stats_map.get(FinancialImportBatch.STATUS_FAILED):
        score -= Decimal('7')
    if import_stats_map.get(FinancialImportBatch.STATUS_PENDING) and (
        import_stats_map.get(FinancialImportBatch.STATUS_PENDING, 0)
        > import_stats_map.get(FinancialImportBatch.STATUS_SUCCESS, 0)
    ):
        score -= Decimal('3')

    gap_ratio = _coalesce_decimal(budget_gap_ratio)
    if gap_ratio < 0:
        score += gap_ratio * Decimal('0.2')

    score = _clamp_percentage(score)

    if score >= Decimal('85'):
        label = 'Eccellente'
        badge_class = 'bg-success-subtle text-success'
        message = 'Performance superiore agli obiettivi: mantieni la spinta commerciale e la disciplina sui costi.'
    elif score >= Decimal('70'):
        label = 'Solida'
        badge_class = 'bg-primary-subtle text-primary'
        message = 'Fundamentali robusti: concentrarsi sulle aree critiche per scalare ulteriormente.'
    elif score >= Decimal('55'):
        label = 'Da monitorare'
        badge_class = 'bg-warning-subtle text-warning'
        message = 'Sono necessari interventi mirati su ricavi o costi per rientrare negli obiettivi annuali.'
    else:
        label = 'Critica'
        badge_class = 'bg-danger-subtle text-danger'
        message = 'Attivare un piano di rientro immediato: margini e ricavi sono sotto pressione.'

    return {
        'score': score,
        'label': label,
        'badge_class': badge_class,
        'message': message,
    }


def _build_strategic_alerts(
    revenue_attainment,
    cost_efficiency,
    margin_coverage,
    budget_gap_ratio,
    import_stats_map,
):
    alerts = []
    if revenue_attainment < Decimal('95'):
        alerts.append(
            {
                'level': 'danger',
                'icon': 'fa-arrow-trend-down',
                'text': 'Ricavi sotto target: pianifica campagne commerciali e cross-selling per recuperare quota.',
            }
        )
    if cost_efficiency > Decimal('105'):
        alerts.append(
            {
                'level': 'warning',
                'icon': 'fa-fire',
                'text': 'Pressione sui costi operativi: rinegozia fornitori e riallinea i budget dei reparti critici.',
            }
        )
    if margin_coverage < Decimal('90'):
        alerts.append(
            {
                'level': 'danger',
                'icon': 'fa-circle-exclamation',
                'text': 'Margine operativo in erosione: ribilancia mix di ricavi premium e ottimizza i processi di spesa.',
            }
        )
    if budget_gap_ratio < Decimal('0'):
        alerts.append(
            {
                'level': 'warning',
                'icon': 'fa-chart-line',
                'text': 'La proiezione annuale indica un gap sul budget: anticipa le azioni correttive.',
            }
        )
    if import_stats_map.get(FinancialImportBatch.STATUS_FAILED):
        alerts.append(
            {
                'level': 'warning',
                'icon': 'fa-link-slash',
                'text': 'Flussi di import falliti: verifica le integrazioni per garantire report tempestivi.',
            }
        )
    if not alerts:
        alerts.append(
            {
                'level': 'success',
                'icon': 'fa-circle-check',
                'text': 'Ottime performance: prosegui con iniziative di innovazione e upselling per guidare il mercato.',
            }
        )
    return alerts


@login_required
@role_required(ALLOWED_ROLES)
def dashboard_view(request):
    user = request.user
    companies = _get_accessible_companies(user)
    if not companies.exists():
        messages.error(request, "Non sei associato a nessuna società da analizzare.")
        return redirect('home')

    selected_company = None
    selected_company_id = request.GET.get('company')
    if selected_company_id:
        try:
            selected_company = companies.get(pk=selected_company_id)
        except Company.DoesNotExist:
            selected_company = None
    elif companies.count() == 1:
        selected_company = companies.first()

    resorts = _get_accessible_resorts(user, selected_company)
    selected_resort = None
    selected_resort_id = request.GET.get('resort')
    if selected_resort_id:
        try:
            selected_resort = resorts.get(pk=selected_resort_id)
        except Resort.DoesNotExist:
            selected_resort = None
    elif getattr(user, 'resort_id', None) and resorts.filter(pk=user.resort_id).exists():
        selected_resort = resorts.filter(pk=user.resort_id).first()

    year_values = (
        FinancialPeriod.objects.filter(company__in=companies)
        .values_list('year', flat=True)
        .distinct()
        .order_by('-year')
    )
    years = list(year_values) or [timezone.now().year]
    selected_year = request.GET.get('year')
    try:
        selected_year = int(selected_year)
    except (TypeError, ValueError):
        selected_year = years[0]

    period_type = request.GET.get('period_type') or FinancialPeriod.PERIOD_MONTHLY

    filter_form = FinancialDashboardFilterForm(
        request.GET or None,
        user=user,
        companies=companies,
        resorts=resorts,
        years=years,
        initial={
            'company': selected_company.pk if selected_company else None,
            'resort': selected_resort.pk if selected_resort else None,
            'year': selected_year,
            'period_type': period_type,
        },
    )

    snapshot_qs = (
        FinancialSnapshot.objects.select_related('period', 'period__company', 'period__resort')
        .filter(period__company__in=companies, period__year=selected_year)
    )
    if selected_company:
        snapshot_qs = snapshot_qs.filter(period__company=selected_company)
    if selected_resort:
        snapshot_qs = snapshot_qs.filter(period__resort=selected_resort)
    if period_type:
        snapshot_qs = snapshot_qs.filter(period__period_type=period_type)

    actual = _aggregate_snapshot(snapshot_qs, FinancialSnapshot.TYPE_ACTUAL)
    budget = _aggregate_snapshot(snapshot_qs, FinancialSnapshot.TYPE_BUDGET)
    previous = _aggregate_snapshot(snapshot_qs, FinancialSnapshot.TYPE_PREVIOUS)
    forecast = _aggregate_snapshot(snapshot_qs, FinancialSnapshot.TYPE_FORECAST)

    variance_budget = actual['margin'] - budget['margin']
    variance_previous = actual['margin'] - previous['margin']

    revenue_attainment = _percentage(actual['revenue'], budget['revenue'])
    cost_efficiency = _percentage(actual['costs'], budget['costs'])
    margin_coverage = _percentage(actual['margin'], budget['margin'])
    revenue_progress = _clamp_percentage(revenue_attainment)
    cost_progress = _clamp_percentage(cost_efficiency)
    margin_progress = _clamp_percentage(margin_coverage)

    yoy_revenue_delta, yoy_revenue_pct = _growth(actual['revenue'], previous['revenue'])
    yoy_cost_delta, yoy_cost_pct = _growth(actual['costs'], previous['costs'])
    yoy_margin_delta, yoy_margin_pct = _growth(actual['margin'], previous['margin'])

    monthly_qs = snapshot_qs.filter(period__period_type=FinancialPeriod.PERIOD_MONTHLY)
    chart_actual = _build_monthly_margin_series(monthly_qs, FinancialSnapshot.TYPE_ACTUAL)
    chart_budget = _build_monthly_margin_series(monthly_qs, FinancialSnapshot.TYPE_BUDGET)
    monthly_totals_map = _build_monthly_totals(monthly_qs, FinancialSnapshot.TYPE_ACTUAL)
    run_rate_projection = _compute_run_rate(actual, monthly_totals_map)
    projected_margin_gap = run_rate_projection['margin'] - budget['margin']
    budget_gap_ratio = (
        _percentage(projected_margin_gap, budget['margin'])
        if budget['margin']
        else Decimal('0')
    )

    top_line_items = (
        FinancialLineItem.objects.select_related('snapshot', 'category')
        .filter(
            snapshot__in=snapshot_qs,
            snapshot__snapshot_type=FinancialSnapshot.TYPE_ACTUAL,
        )
        .order_by('-amount')[:5]
    )

    po_items = PurchaseOrderItem.objects.filter(purchase_order__created_at__year=selected_year)
    po_items = po_items.filter(purchase_order__status__in=['approved', 'completed'])
    if selected_company:
        po_items = po_items.filter(purchase_order__resort__company=selected_company)
    else:
        po_items = po_items.filter(purchase_order__resort__company__in=companies)
    if selected_resort:
        po_items = po_items.filter(purchase_order__resort=selected_resort)

    purchase_order_monthly = _build_purchase_order_series(po_items)
    purchase_order_total = _coalesce_decimal(
        po_items.aggregate(
            total=Coalesce(
                Sum(F('quantity') * F('unit_price'), output_field=DecimalField(max_digits=16, decimal_places=2)),
                Decimal('0'),
            )
        )['total']
    )

    economato_qs = EconomatoRequest.objects.filter(created_at__year=selected_year)
    if selected_company:
        economato_qs = economato_qs.filter(company=selected_company)
    else:
        economato_qs = economato_qs.filter(company__in=companies)
    if selected_resort:
        economato_qs = economato_qs.filter(resort=selected_resort)
    economato_qs = economato_qs.filter(status__in=[
        EconomatoRequest.STATUS_APPROVED,
        EconomatoRequest.STATUS_FULFILLED,
    ])
    economato_total = _coalesce_decimal(
        economato_qs.aggregate(total=Coalesce(Sum('total_estimated_cost'), Decimal('0')))['total']
    )

    economato_by_cost_center_raw = (
        economato_qs.values('cost_center__code', 'cost_center__name')
        .annotate(total=Coalesce(Sum('total_estimated_cost'), Decimal('0')))
        .order_by('-total')[:5]
    )
    economato_by_cost_center = [
        {
            'code': entry['cost_center__code'],
            'name': entry['cost_center__name'],
            'total': _coalesce_decimal(entry['total']),
        }
        for entry in economato_by_cost_center_raw
    ]

    economato_monthly_map = {month: Decimal('0') for month in range(1, 13)}
    for entry in (
        economato_qs.annotate(month=ExtractMonth('created_at'))
        .values('month')
        .annotate(total=Coalesce(Sum('total_estimated_cost'), Decimal('0')))
    ):
        month = entry['month'] or 0
        if month:
            economato_monthly_map[month] = _coalesce_decimal(entry['total'])
    economato_monthly = [float(economato_monthly_map[month]) for month in range(1, 13)]

    budget_qs = Budget.objects.filter(year=selected_year)
    if selected_company:
        budget_qs = budget_qs.filter(resort__company=selected_company)
    else:
        budget_qs = budget_qs.filter(resort__company__in=companies)
    if selected_resort:
        budget_qs = budget_qs.filter(resort=selected_resort)
    budget_total = _coalesce_decimal(budget_qs.aggregate(total=Coalesce(Sum('amount'), Decimal('0')))['total'])

    purchase_order_budget_ratio = _percentage(purchase_order_total, budget_total) if budget_total else Decimal('0')
    economato_budget_ratio = _percentage(economato_total, budget_total) if budget_total else Decimal('0')

    category_aggregates = (
        FinancialLineItem.objects.filter(snapshot__in=snapshot_qs, category__isnull=False)
        .values('category__id', 'category__name', 'category__color', 'category__category_type')
        .annotate(
            actual_amount=Coalesce(
                Sum('amount', filter=Q(snapshot__snapshot_type=FinancialSnapshot.TYPE_ACTUAL)),
                Decimal('0'),
            ),
            budget_amount=Coalesce(
                Sum('amount', filter=Q(snapshot__snapshot_type=FinancialSnapshot.TYPE_BUDGET)),
                Decimal('0'),
            ),
            previous_amount=Coalesce(
                Sum('amount', filter=Q(snapshot__snapshot_type=FinancialSnapshot.TYPE_PREVIOUS)),
                Decimal('0'),
            ),
        )
    )

    category_breakdown = []
    for entry in category_aggregates:
        actual_amount = _coalesce_decimal(entry['actual_amount'])
        budget_amount = _coalesce_decimal(entry['budget_amount'])
        previous_amount = _coalesce_decimal(entry['previous_amount'])
        variance = actual_amount - budget_amount
        coverage = _percentage(actual_amount, budget_amount) if budget_amount else Decimal('0')
        variance_pct = _percentage(variance, budget_amount) if budget_amount else Decimal('0')
        yoy_delta, yoy_pct = _growth(actual_amount, previous_amount)
        color = entry['category__color'] or ''
        if not color:
            if entry['category__category_type'] == FinancialLineItem.LINE_REVENUE:
                color = '#198754'
            else:
                color = '#dc3545'
        category_breakdown.append(
            {
                'id': entry['category__id'],
                'name': entry['category__name'] or 'Senza categoria',
                'type': entry['category__category_type'],
                'actual': actual_amount,
                'budget': budget_amount,
                'variance': variance,
                'coverage': coverage,
                'variance_pct': variance_pct,
                'yoy_delta': yoy_delta,
                'yoy_pct': yoy_pct,
                'color': color,
            }
        )

    category_breakdown.sort(key=lambda entry: abs(entry['variance']), reverse=True)
    category_chart_data = category_breakdown[:6]
    category_table = category_breakdown[:8]
    category_chart_labels = [entry['name'] for entry in category_chart_data]
    category_chart_actual = [float(entry['actual']) for entry in category_chart_data]
    category_chart_budget = [float(entry['budget']) for entry in category_chart_data]
    category_chart_colors = [entry['color'] for entry in category_chart_data]

    strategic_opportunities = []
    revenue_opportunities = [
        entry
        for entry in category_breakdown
        if entry['type'] == FinancialLineItem.LINE_REVENUE and entry['variance'] > 0
    ]
    cost_opportunities = [
        entry
        for entry in category_breakdown
        if entry['type'] == FinancialLineItem.LINE_COST and entry['coverage'] < Decimal('95')
    ]
    revenue_opportunities.sort(key=lambda entry: entry['variance'], reverse=True)
    cost_opportunities.sort(key=lambda entry: entry['coverage'])
    for entry in revenue_opportunities[:2]:
        strategic_opportunities.append(
            {
                'name': entry['name'],
                'kind': 'growth',
                'variance': entry['variance'],
                'coverage': entry['coverage'],
                'yoy_pct': entry['yoy_pct'],
            }
        )
    for entry in cost_opportunities[:2]:
        strategic_opportunities.append(
            {
                'name': entry['name'],
                'kind': 'efficiency',
                'variance': entry['variance'],
                'coverage': entry['coverage'],
                'yoy_pct': entry['yoy_pct'],
            }
        )

    import_batches_qs = (
        FinancialImportBatch.objects.filter(snapshots__period__company__in=companies)
        .distinct()
    )
    if selected_company:
        import_batches_qs = import_batches_qs.filter(snapshots__period__company=selected_company)
    if selected_resort:
        import_batches_qs = import_batches_qs.filter(snapshots__period__resort=selected_resort)
    import_stats_map = {status: 0 for status, _ in FinancialImportBatch.STATUS_CHOICES}
    for stat in import_batches_qs.values('status').annotate(count=Count('id')):
        import_stats_map[stat['status']] = stat['count']
    health_meta = _compute_health_metadata(
        revenue_attainment,
        cost_efficiency,
        margin_coverage,
        import_stats_map,
        budget_gap_ratio,
    )
    strategic_alerts = _build_strategic_alerts(
        revenue_attainment,
        cost_efficiency,
        margin_coverage,
        budget_gap_ratio,
        import_stats_map,
    )
    recent_import_batches = list(import_batches_qs.select_related('data_source').order_by('-started_at')[:5])
    total_import_batches = sum(import_stats_map.values())
    import_statuses = [
        {
            'code': status,
            'label': label,
            'count': import_stats_map.get(status, 0),
        }
        for status, label in FinancialImportBatch.STATUS_CHOICES
    ]

    context = {
        'filter_form': filter_form,
        'selected_company': selected_company,
        'selected_resort': selected_resort,
        'selected_year': selected_year,
        'period_type': period_type,
        'actual_totals': actual,
        'budget_totals': budget,
        'previous_totals': previous,
        'forecast_totals': forecast,
        'variance_budget': variance_budget,
        'variance_previous': variance_previous,
        'revenue_attainment': revenue_attainment,
        'revenue_attainment_progress': revenue_progress,
        'cost_efficiency': cost_efficiency,
        'cost_efficiency_progress': cost_progress,
        'margin_coverage': margin_coverage,
        'margin_coverage_progress': margin_progress,
        'yoy_revenue_delta': yoy_revenue_delta,
        'yoy_revenue_pct': yoy_revenue_pct,
        'yoy_cost_delta': yoy_cost_delta,
        'yoy_cost_pct': yoy_cost_pct,
        'yoy_margin_delta': yoy_margin_delta,
        'yoy_margin_pct': yoy_margin_pct,
        'chart_labels': [
            timezone.datetime(selected_year, month, 1).strftime('%b') for month in range(1, 13)
        ],
        'chart_actual': chart_actual,
        'chart_budget': chart_budget,
        'top_line_items': top_line_items,
        'purchase_order_monthly': purchase_order_monthly,
        'purchase_order_total': purchase_order_total,
        'economato_total': economato_total,
        'economato_monthly': economato_monthly,
        'economato_by_cost_center': economato_by_cost_center,
        'budget_total': budget_total,
        'purchase_order_budget_ratio': purchase_order_budget_ratio,
        'economato_budget_ratio': economato_budget_ratio,
        'category_table': category_table,
        'category_chart_labels': category_chart_labels,
        'category_chart_actual': category_chart_actual,
        'category_chart_budget': category_chart_budget,
        'category_chart_colors': category_chart_colors,
        'run_rate_totals': run_rate_projection,
        'run_rate_months': run_rate_projection['months_recorded'],
        'run_rate_factor': run_rate_projection['factor'],
        'projected_margin_gap': projected_margin_gap,
        'budget_gap_ratio': budget_gap_ratio,
        'health_score': health_meta['score'],
        'health_label': health_meta['label'],
        'health_badge_class': health_meta['badge_class'],
        'health_message': health_meta['message'],
        'strategic_alerts': strategic_alerts,
        'strategic_opportunities': strategic_opportunities,
        'recent_import_batches': recent_import_batches,
        'total_import_batches': total_import_batches,
        'import_statuses': import_statuses,
    }
    context['in_app_guide'] = build_financials_guide(request.user)
    return themed_render(request, 'financials/dashboard.html', context)


@login_required
@role_required(ALLOWED_ROLES)
def snapshot_list_view(request):
    user = request.user
    companies = _get_accessible_companies(user)
    if not companies.exists():
        messages.error(request, "Non hai società associate per consultare i dati.")
        return redirect('home')

    selected_company = None
    company_id = request.GET.get('company')
    if company_id:
        try:
            selected_company = companies.get(pk=company_id)
        except Company.DoesNotExist:
            selected_company = None
    elif companies.count() == 1:
        selected_company = companies.first()

    resorts = _get_accessible_resorts(user, selected_company)

    year_values = (
        FinancialPeriod.objects.filter(company__in=companies)
        .values_list('year', flat=True)
        .distinct()
        .order_by('-year')
    )
    years = list(year_values) or [timezone.now().year]

    filter_form = FinancialSnapshotFilterForm(
        request.GET or None,
        user=user,
        companies=companies,
        resorts=resorts,
        years=years,
        initial={
            'company': selected_company.pk if selected_company else None,
            'year': years[0],
        },
    )

    snapshots = FinancialSnapshot.objects.select_related(
        'period', 'period__company', 'period__resort', 'data_source'
    ).filter(period__company__in=companies)

    if filter_form.is_valid():
        cleaned = filter_form.cleaned_data
        company = cleaned.get('company') or selected_company
        resort = cleaned.get('resort')
        year = cleaned.get('year')
        period_type = cleaned.get('period_type')
        snapshot_type = cleaned.get('snapshot_type')

        if company:
            snapshots = snapshots.filter(period__company=company)
        if resort:
            snapshots = snapshots.filter(period__resort=resort)
        if year:
            snapshots = snapshots.filter(period__year=year)
        if period_type:
            snapshots = snapshots.filter(period__period_type=period_type)
        if snapshot_type:
            snapshots = snapshots.filter(snapshot_type=snapshot_type)

    snapshots = snapshots.order_by('-period__year', '-period__month', 'snapshot_type')

    context = {
        'filter_form': filter_form,
        'snapshots': snapshots,
        'selected_company': selected_company,
    }
    return themed_render(request, 'financials/snapshot_list.html', context)


@login_required
@role_required(ALLOWED_ROLES)
def snapshot_create_view(request):
    user = request.user
    companies = _get_accessible_companies(user)
    if not companies.exists():
        messages.error(request, "Non hai società associate per creare dati finanziari.")
        return redirect('financials:dashboard')

    empty_snapshot = FinancialSnapshot()

    if request.method == 'POST':
        form = FinancialSnapshotForm(request.POST, user=user, companies=companies)
        formset = FinancialLineItemFormSet(request.POST, instance=empty_snapshot, user=user, companies=companies)
        if form.is_valid() and formset.is_valid():
            snapshot = form.save(commit=False)
            snapshot.created_by = user
            snapshot.save()
            formset.instance = snapshot
            formset.save()
            if form.cleaned_data.get('recalculate_totals'):
                snapshot.recalculate_totals(save=True)
            messages.success(request, "Snapshot finanziario creato con successo.")
            return redirect('financials:snapshot_list')
    else:
        form = FinancialSnapshotForm(user=user, companies=companies)
        formset = FinancialLineItemFormSet(instance=empty_snapshot, user=user, companies=companies)

    return themed_render(
        request,
        'financials/snapshot_form.html',
        {
            'form': form,
            'formset': formset,
            'title': 'Nuovo Snapshot Finanziario',
        },
    )


@login_required
@role_required(ALLOWED_ROLES)
def snapshot_update_view(request, pk):
    user = request.user
    snapshot = get_object_or_404(FinancialSnapshot, pk=pk)
    companies = _get_accessible_companies(user)
    if not companies.filter(pk=snapshot.period.company_id).exists():
        messages.error(request, "Non hai i permessi per modificare questo record.")
        return redirect('financials:snapshot_list')

    if request.method == 'POST':
        form = FinancialSnapshotForm(request.POST, instance=snapshot, user=user, companies=companies)
        formset = FinancialLineItemFormSet(request.POST, instance=snapshot, user=user, companies=companies)
        if form.is_valid() and formset.is_valid():
            snapshot = form.save()
            formset.save()
            if form.cleaned_data.get('recalculate_totals'):
                snapshot.recalculate_totals(save=True)
            messages.success(request, "Snapshot finanziario aggiornato correttamente.")
            return redirect('financials:snapshot_list')
    else:
        form = FinancialSnapshotForm(instance=snapshot, user=user, companies=companies)
        formset = FinancialLineItemFormSet(instance=snapshot, user=user, companies=companies)

    return themed_render(
        request,
        'financials/snapshot_form.html',
        {
            'form': form,
            'formset': formset,
            'title': f'Modifica Snapshot: {snapshot}',
        },
    )


@login_required
@role_required(ALLOWED_ROLES)
def period_create_view(request):
    user = request.user
    companies = _get_accessible_companies(user)
    if not companies.exists():
        messages.error(request, "Nessuna società associata all'utente.")
        return redirect('financials:dashboard')

    if request.method == 'POST':
        form = FinancialPeriodForm(request.POST, user=user, companies=companies)
        if form.is_valid():
            period = form.save()
            messages.success(request, f"Periodo {period.label} creato correttamente.")
            return redirect('financials:snapshot_list')
    else:
        form = FinancialPeriodForm(user=user, companies=companies)

    return themed_render(
        request,
        'financials/period_form.html',
        {
            'form': form,
            'title': 'Nuovo Periodo Finanziario',
        },
    )


@login_required
@role_required(ALLOWED_ROLES)
def period_update_view(request, pk):
    user = request.user
    period = get_object_or_404(FinancialPeriod, pk=pk)
    companies = _get_accessible_companies(user)
    if not companies.filter(pk=period.company_id).exists():
        messages.error(request, "Non hai i permessi per modificare questo periodo.")
        return redirect('financials:snapshot_list')

    if request.method == 'POST':
        form = FinancialPeriodForm(request.POST, instance=period, user=user, companies=companies)
        if form.is_valid():
            period = form.save()
            messages.success(request, f"Periodo {period.label} aggiornato correttamente.")
            return redirect('financials:snapshot_list')
    else:
        form = FinancialPeriodForm(instance=period, user=user, companies=companies)

    return themed_render(
        request,
        'financials/period_form.html',
        {
            'form': form,
            'title': f'Modifica Periodo: {period.label}',
        },
    )


@login_required
@role_required(ALLOWED_ROLES)
def snapshot_delete_view(request, pk):
    user = request.user
    snapshot = get_object_or_404(FinancialSnapshot, pk=pk)
    companies = _get_accessible_companies(user)
    if not companies.filter(pk=snapshot.period.company_id).exists():
        messages.error(request, "Non hai i permessi per eliminare questo record.")
        return redirect('financials:snapshot_list')

    if request.method == 'POST':
        period = snapshot.period
        snapshot.delete()
        messages.success(request, f"Snapshot per {period} eliminato.")
        return redirect('financials:snapshot_list')

    return themed_render(
        request,
        'financials/snapshot_confirm_delete.html',
        {
            'snapshot': snapshot,
        },
    )
