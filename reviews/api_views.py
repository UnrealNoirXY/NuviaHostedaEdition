import json
from collections import defaultdict
from datetime import datetime, timedelta
from types import SimpleNamespace

from django.db.models import Avg, Count, Q, F, Case, When, FloatField
from django.db.models.functions import Coalesce, TruncMonth, Round
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from .models import Review, ReviewAnalysis, Resort, ReviewSource, VeratourReport
from accounts.models import User

def _get_analysis_center_filtered_reviews(request):
    user = request.user
    reviews = Review.objects.select_related('analysis', 'source', 'resort').all()

    SYNONYM_MAP = {
        'piscina': ['piscina', 'vasca', 'solarium', 'cloro'],
        'personale': ['personale', 'staff', 'team', 'camerieri', 'reception', 'gentilezza', 'disponibilità'],
        'pulizia': ['pulizia', 'pulito', 'igiene', 'sporco', 'ordine', 'sanificazione'],
        'cibo': ['cibo', 'ristorazione', 'colazione', 'cena', 'pranzo', 'buffet', 'qualità'],
        'camera': ['camera', 'stanza', 'suite', 'letto', 'bagno', 'alloggio'],
    }

    # Apply permissions
    if user.role in [User.OWNER, User.CORPORATE, User.RISORSE_UMANE, User.CAPO_ECONOMO, User.HEAD_MAINTAINER]:
        if user.company:
            reviews = reviews.filter(resort__company=user.company)
        else:
            reviews = reviews.none()
    elif user.role == User.DIRECTOR:
        if user.resort:
            reviews = reviews.filter(resort=user.resort)
        else:
            reviews = reviews.none()

    # Apply filters from request
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    resort_ids_str = request.GET.get('resorts')
    source_ids_str = request.GET.get('sources')

    if resort_ids_str:
        resort_ids = [int(id) for id in resort_ids_str.split(',') if id.strip()]
        if user.role == User.DIRECTOR:
            if user.resort and user.resort.id in resort_ids:
                 reviews = reviews.filter(resort_id=user.resort.id)
            else:
                 reviews = reviews.none()
        else:
            reviews = reviews.filter(resort_id__in=resort_ids)

    include_internal = request.GET.get('include_internal', 'false').lower() == 'true'
    veratour_source = ReviewSource.objects.filter(name='Veratour').first()

    if source_ids_str:
        source_ids = [int(id) for id in source_ids_str.split(',') if id.strip()]
        if include_internal and veratour_source and veratour_source.id not in source_ids:
            source_ids.append(veratour_source.id)
        reviews = reviews.filter(source_id__in=source_ids)
    elif not include_internal:
        # Default: Exclude Veratour if not explicitly requested via source_ids
        # AND include_internal is false.
        if veratour_source:
            reviews = reviews.exclude(source=veratour_source)

    query = request.GET.get('query', '').strip().lower()
    if query:
        terms = SYNONYM_MAP.get(query, [query])
        q_objects = Q()
        for term in terms:
            q_objects |= Q(text__icontains=term)
        reviews = reviews.filter(q_objects)

    if start_date_str:
        reviews = reviews.filter(review_date__gte=start_date_str)

    if end_date_str:
        end_date = (
            datetime.strptime(end_date_str, "%Y-%m-%d") + timedelta(days=1)
        ).strftime('%Y-%m-%d')
        reviews = reviews.filter(review_date__lt=end_date)

    return reviews


def _shift_date_back_one_year(date_obj):
    """Shift a date object back by one calendar year, handling leap years."""
    try:
        return date_obj.replace(year=date_obj.year - 1)
    except ValueError:
        # Handle February 29th by falling back to 365 days difference
        return date_obj - timedelta(days=365)

def _get_previous_period_reviews(request, reviews_qs=None):
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')

    # If dates are missing, determine the implicit range from current reviews
    if not start_date_str or not end_date_str:
        if reviews_qs is None:
            reviews_qs = _get_analysis_center_filtered_reviews(request)

        if not start_date_str:
            first_review = reviews_qs.order_by('review_date').first()
            if first_review:
                start_date_str = first_review.review_date.date().isoformat()

        if not end_date_str:
            last_review = reviews_qs.order_by('-review_date').first()
            if last_review:
                end_date_str = last_review.review_date.date().isoformat()

    if not start_date_str:
         return Review.objects.none()

    previous_params = request.GET.copy()
    current_start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
    previous_start_date = _shift_date_back_one_year(current_start_date)
    previous_params['start_date'] = previous_start_date.strftime('%Y-%m-%d')

    if end_date_str:
        current_end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
        previous_end_date = _shift_date_back_one_year(current_end_date)
        previous_params['end_date'] = previous_end_date.strftime('%Y-%m-%d')

    previous_request = SimpleNamespace(user=request.user, GET=previous_params)
    return _get_analysis_center_filtered_reviews(previous_request)


def _get_by_resort_data(request, func):
    resort_ids_str = request.GET.get('resorts')
    by_resort = {}
    if resort_ids_str and ',' in resort_ids_str:
        resort_ids = [int(id) for id in resort_ids_str.split(',') if id.strip()]
        for rid in resort_ids:
            params = request.GET.copy()
            params['resorts'] = str(rid)
            # Ensure resorts is overridden to a single value for per-resort filtering
            mock_req = SimpleNamespace(user=request.user, GET=params)
            by_resort[str(rid)] = func(mock_req)
    return by_resort

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def kpi_summary_data(request):
    normalized_rating_expr = Case(
        When(source__name='Booking.com', then=F('rating') / 2),
        When(source__name='Veratour', then=F('rating') / 2),
        default=F('rating'),
        output_field=FloatField()
    )

    def get_stats_internal(req):
        reviews = _get_analysis_center_filtered_reviews(req)
        previous_reviews = _get_previous_period_reviews(req, reviews)

        def get_stats(qs):
            stats = qs.annotate(
                normalized_rating=normalized_rating_expr
            ).aggregate(
                total_reviews=Count('id'),
                avg_rating=Coalesce(Avg('normalized_rating'), 0.0),
                avg_sentiment=Coalesce(Avg('analysis__sentiment_score'), 0.0),
                negative_reviews=Count('id', filter=Q(rating__lt=5)),
                anomalies_count=Count('id', filter=Q(analysis__is_anomaly=True))
            )
            return {
                'total_reviews': stats['total_reviews'],
                'average_rating': round(stats['avg_rating'], 2),
                'average_sentiment': round(stats['avg_sentiment'], 2),
                'negative_reviews': stats['negative_reviews'],
                'anomalies_count': stats['anomalies_count'],
            }

        current_stats = get_stats(reviews)
        previous_stats = get_stats(previous_reviews)

        # Veratour Specific logic
        veratour_source = ReviewSource.objects.filter(name='Veratour').first()
        is_veratour_selected = False
        source_ids_str = req.GET.get('sources')
        if veratour_source:
            if not source_ids_str or (source_ids_str.strip() != "" and str(veratour_source.id) in [id.strip() for id in source_ids_str.split(',')]):
                is_veratour_selected = True

        critical_alert = None
        response_rate = None
        sample_reliability = None
        total_guests = 0
        max_capacity = 0
        cross_analysis = []

        if is_veratour_selected and veratour_source:
            veratour_reviews = reviews.filter(source=veratour_source)
            veratour_count = veratour_reviews.count()
            # In 1-10 scale, negative is < 5 (Cluster 1 & 2)
            veratour_negatives = veratour_reviews.filter(rating__lt=5).count()

            # Get Totale Ospiti (Veratour reports can span multiple weeks, we want the sum in the period)
            resort_ids_str = req.GET.get('resorts')
            reports = VeratourReport.objects.all()
            if resort_ids_str:
                reports = reports.filter(resort_id__in=[int(id) for id in resort_ids_str.split(',') if id.strip()])

            start_date = req.GET.get('start_date')
            end_date = req.GET.get('end_date')

            # Use overlapping logic for reports
            if start_date:
                reports = reports.filter(end_date__gte=start_date)
            if end_date:
                reports = reports.filter(start_date__lte=end_date)

            from django.db.models import Sum, Max
            report_aggr = reports.aggregate(
                total=Coalesce(Sum('total_guests'), 0)
            )
            total_guests = report_aggr['total'] or 0

            # Group by resort to avoid summing multiple reports of the same resort in the denominator
            resort_capacities = reports.values('resort').annotate(max_cap=Max('max_capacity'))
            max_capacity = sum(item['max_cap'] or 0 for item in resort_capacities)

            if total_guests > 0:
                response_rate = round((veratour_count / total_guests) * 100, 1)

            sample_reliability = None
            if total_guests > 0:
                # Reliability check: < 15% of total cards
                is_low_sample = (veratour_count / total_guests) < 0.15
                sample_reliability = "Indicativo - Campione Ridotto" if is_low_sample else "Affidabile"

            # Cross-Analysis Data
            cross_analysis = []
            # Merge all report data from selected reports
            merged_report_data = {}
            for r in reports:
                for dept, dstats in r.data.items():
                    if dept not in merged_report_data:
                        merged_report_data[dept] = {"pos": [], "neg": []}
                    merged_report_data[dept]["pos"].append(dstats.get("positive", 0))
                    merged_report_data[dept]["neg"].append(dstats.get("negative", 0))

            # Calculate Sentiment IA by department
            # We stored matched departments in 'keywords' JSONField of ReviewAnalysis
            # Note: reviews_qs is already filtered by date and resort.
            veratour_reviews = reviews.filter(source=veratour_source)

            for dept, stats in merged_report_data.items():
                avg_report_pos = sum(stats["pos"]) / len(stats["pos"]) if stats["pos"] else 0
                avg_report_neg = sum(stats["neg"]) / len(stats["neg"]) if stats["neg"] else 0

                # Sentiment IA for this department
                # We use icontains for compatibility with SQLite which doesn't support 'contains' on JSONField lists.
                # Since we store depts as a list ["DEPT1", "DEPT2"], icontains "DEPT1" will match.
                dept_reviews = veratour_reviews.filter(analysis__keywords__icontains=dept)
                dept_count = dept_reviews.count()

                # We calculate IA Positive % and IA Negative %
                # Sentiment score is 1-10. Pos >= 7, Neg < 5
                ia_pos_count = dept_reviews.filter(rating__gte=7).count()
                ia_neg_count = dept_reviews.filter(rating__lt=5).count()

                ia_pos_pct = round((ia_pos_count / dept_count * 100), 1) if dept_count > 0 else 0
                ia_neg_pct = round((ia_neg_count / dept_count * 100), 1) if dept_count > 0 else 0

                # Gap calculation (using Negative % as requested in Alert logic)
                # But for the table we can show Positives too.
                gap = round(ia_neg_pct - avg_report_neg, 1)

                cross_analysis.append({
                    "department": dept,
                    "report_pos": round(avg_report_pos, 1),
                    "report_neg": round(avg_report_neg, 1),
                    "ia_pos": ia_pos_pct,
                    "ia_neg": ia_neg_pct,
                    "gap": gap,
                    "count": dept_count,
                    "alert": gap > 5,
                    "critical": gap > 10
                })

            # Alert logic: negative > 10% of voters (General)
            if veratour_count > 0:
                # Use GENERAL report negative if available, else fallback to calculation
                general_report_neg = merged_report_data.get("GENERAL", {}).get("neg", [0])[0]

                # Sentiment IA Neg %
                ia_total_neg = veratour_reviews.filter(rating__lt=5).count()
                ia_total_neg_pct = (ia_total_neg / veratour_count) * 100

                discrepancy_gap = ia_total_neg_pct - general_report_neg

                if discrepancy_gap > 5:
                    impact_total = round((ia_total_neg / max_capacity) * 100, 1) if max_capacity > 0 else 0
                    critical_alert = {
                        'title': 'Discrepanza Rilevata',
                        'level': 'critical' if discrepancy_gap > 10 else 'warning',
                        'message': f"Il feedback testuale è più critico dei dati quantitativi. IA rileva {ia_total_neg_pct:.1f}% di negatività vs {general_report_neg:.1f}% del Report. Impatto reale sulla platea totale: {impact_total}%."
                    }

        return {
            'current': current_stats,
            'previous': previous_stats,
            'veratour': {
                'response_rate': response_rate,
                    'sample_reliability': sample_reliability,
                'total_guests': total_guests,
                'max_capacity': max_capacity,
                'critical_alert': critical_alert,
                'cross_analysis': cross_analysis
            }
        }

    overall = get_stats_internal(request)
    by_resort = _get_by_resort_data(request, get_stats_internal)

    return JsonResponse({
        'overall': overall,
        'by_resort': by_resort
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def trend_chart_data(request):
    normalized_rating_expr = Case(
        When(source__name='Booking.com', then=F('rating') / 2),
        When(source__name='Veratour', then=F('rating') / 2),
        default=F('rating'),
        output_field=FloatField()
    )

    def get_trend_data_internal(req):
        reviews = _get_analysis_center_filtered_reviews(req)
        previous_reviews = _get_previous_period_reviews(req, reviews)

        def get_trend(qs):
            return qs.annotate(
                month=TruncMonth('review_date'),
                normalized_rating=normalized_rating_expr
            ).values('month').annotate(
                avg_rating=Avg('normalized_rating'),
                avg_sentiment=Avg('analysis__sentiment_score'),
                review_count=Count('id')
            ).order_by('month')

        current_trend = list(get_trend(reviews))

        # Add occupancy data to trend if possible
        resort_ids_str = req.GET.get('resorts')

        # Pre-fetch all relevant reports to avoid N+1 queries
        all_reports_qs = VeratourReport.objects.all()
        if resort_ids_str:
            all_reports_qs = all_reports_qs.filter(resort_id__in=[int(id) for id in resort_ids_str.split(',') if id.strip()])

        # Filter reports by overall date range if possible
        if current_trend:
            overall_start = current_trend[0]['month'].date()
            overall_end = (current_trend[-1]['month'] + timedelta(days=32)).replace(day=1).date()
            all_reports_qs = all_reports_qs.filter(end_date__gte=overall_start, start_date__lt=overall_end)

        all_reports = list(all_reports_qs)

        for entry in current_trend:
            month_start = entry['month'].date()
            # next month
            month_end = (entry['month'] + timedelta(days=32)).replace(day=1).date()

            # Filter reports that overlap with this month in-memory
            month_reports = [
                r for r in all_reports
                if r.start_date < month_end and r.end_date >= month_start
            ]

            total_g = sum(r.total_guests for r in month_reports)

            # Group by resort to find max capacity per resort in this month
            resort_caps = {}
            for r in month_reports:
                resort_caps[r.resort_id] = max(resort_caps.get(r.resort_id, 0), r.max_capacity)

            month_max_capacity = sum(resort_caps.values())

            occupancy = 0
            if month_max_capacity > 0:
                occupancy = round((total_g / month_max_capacity) * 100, 1)

            entry['occupancy'] = occupancy
        previous_trend = get_trend(previous_reviews)

        return {
            'labels': [d['month'].strftime('%Y-%m') for d in current_trend],
            'datasets': [
                {
                    'label': 'Valutazione Media',
                    'data': [round(d['avg_rating'], 2) if d['avg_rating'] else 0 for d in current_trend],
                    'yAxisID': 'y-axis-rating',
                },
                {
                    'label': 'Sentiment Medio',
                    'data': [round(d['avg_sentiment'], 2) if d['avg_sentiment'] else 0 for d in current_trend],
                    'yAxisID': 'y-axis-sentiment',
                },
                {
                    'label': 'Numero Recensioni',
                    'data': [d['review_count'] for d in current_trend],
                    'yAxisID': 'y-axis-count',
                },
                {
                    'label': 'Occupazione (%)',
                    'data': [d.get('occupancy', 0) for d in current_trend],
                    'yAxisID': 'y-axis-occupancy',
                    'type': 'bar',
                },
                {
                    'label': 'Valutazione Media (Anno Prec.)',
                    'data': [round(d['avg_rating'], 2) if d['avg_rating'] else 0 for d in previous_trend],
                    'yAxisID': 'y-axis-rating',
                    'borderDash': [5, 5],
                    'hidden': True,
                },
                {
                    'label': 'Sentiment Medio (Anno Prec.)',
                    'data': [round(d['avg_sentiment'], 2) if d['avg_sentiment'] else 0 for d in previous_trend],
                    'yAxisID': 'y-axis-sentiment',
                    'borderDash': [5, 5],
                    'hidden': True,
                }
            ]
        }

    overall = get_trend_data_internal(request)
    by_resort = _get_by_resort_data(request, get_trend_data_internal)

    return JsonResponse({
        'overall': overall,
        'by_resort': by_resort
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def platform_chart_data(request):
    reviews = _get_analysis_center_filtered_reviews(request)

    normalized_rating_expr = Case(
        When(source__name='Booking.com', then=F('rating') / 2),
        When(source__name='Veratour', then=F('rating') / 2),
        default=F('rating'),
        output_field=FloatField()
    )

    platform_data = reviews.annotate(
        normalized_rating=normalized_rating_expr
    ).values('source__name').annotate(
        review_count=Count('id'),
        avg_rating=Avg('normalized_rating')
    ).order_by('-review_count')

    platform_widget_data = {
        'labels': [p['source__name'] for p in platform_data],
        'datasets': [
            {
                'label': 'Numero di Recensioni',
                'data': [p['review_count'] for p in platform_data],
            },
            {
                'label': 'Valutazione Media',
                'data': [round(p['avg_rating'], 2) if p['avg_rating'] else 0 for p in platform_data],
            }
        ]
    }

    return JsonResponse(platform_widget_data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def thematic_analysis_data(request):
    reviews = _get_analysis_center_filtered_reviews(request)

    thematic_categories = {
        'Pulizia': ['pulizia', 'pulito', 'igiene', 'sporco', 'macchie'],
        'Servizio': ['servizio', 'staff', 'personale', 'gentile', 'disponibile', 'scortese'],
        'Camere': ['camera', 'stanza', 'spaziosa', 'piccola', 'letto', 'bagno'],
        'Colazione': ['colazione', 'cibo', 'buffet', 'pasticceria', 'cappuccino'],
        'Posizione': ['posizione', 'vista', 'centro', 'vicino', 'lontano'],
    }

    category_ratings = {category: [] for category in thematic_categories}

    for review in reviews:
        text = review.text.lower()
        for category, keywords in thematic_categories.items():
            if any(keyword in text for keyword in keywords):
                # Normalize rating before adding it to the list
                rating = review.rating / 2 if review.source.name == 'Booking.com' else review.rating
                category_ratings[category].append(rating)

    thematic_analysis_data = {
        'labels': [],
        'datasets': [{'label': 'Rating Medio', 'data': []}]
    }
    for category, ratings in category_ratings.items():
        if ratings:
            avg_rating = sum(ratings) / len(ratings)
            thematic_analysis_data['labels'].append(category)
            thematic_analysis_data['datasets'][0]['data'].append(round(avg_rating, 2))

    return JsonResponse(thematic_analysis_data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def reviews_table_data(request):
    reviews = _get_analysis_center_filtered_reviews(request)

    reviews_table_data = list(reviews.order_by('-review_date')[:100].values(
        'id', 'author', 'rating', 'review_date', 'text', 'source__name', 'resort__name',
        'analysis__is_anomaly', 'analysis__keywords', 'analysis__sentiment_score', 'analysis__sentiment_label'
    ))

    return JsonResponse({'reviews': reviews_table_data})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def rating_distribution_data(request):
    def get_distribution_internal(req):
        reviews = _get_analysis_center_filtered_reviews(req)

        # Determine the explicit or implicit period for the current selection
        start_date_str = req.GET.get('start_date')
        end_date_str = req.GET.get('end_date')

        def _extract_period_bounds():
            curr_start = start_date_str
            curr_end = end_date_str

            if not curr_start:
                first_review = reviews.order_by('review_date').first()
                if first_review:
                    curr_start = first_review.review_date.date().isoformat()

            if not curr_end:
                last_review = reviews.order_by('-review_date').first()
                if last_review:
                    curr_end = last_review.review_date.date().isoformat()

            return curr_start, curr_end

        current_start, current_end = _extract_period_bounds()

        # Prepare previous period parameters by shifting the identified dates by one year
        previous_params = req.GET.copy()

        if current_start:
            current_start_date = datetime.strptime(current_start, "%Y-%m-%d").date()
            previous_start_date = _shift_date_back_one_year(current_start_date)
            previous_params['start_date'] = previous_start_date.strftime('%Y-%m-%d')
        elif 'start_date' in previous_params:
            del previous_params['start_date']

        if current_end:
            current_end_date = datetime.strptime(current_end, "%Y-%m-%d").date()
            previous_end_date = _shift_date_back_one_year(current_end_date)
            previous_params['end_date'] = previous_end_date.strftime('%Y-%m-%d')
        elif 'end_date' in previous_params:
            del previous_params['end_date']

        previous_request = SimpleNamespace(user=req.user, GET=previous_params)
        previous_reviews = _get_analysis_center_filtered_reviews(previous_request)

        def _rating_scale_for_source(source_name):
            if not source_name: return 5
            name_lower = source_name.lower()
            if 'booking' in name_lower or 'veratour' in name_lower:
                return 10
            return 5

        def _aggregate_counts(review_queryset):
            source_counts = defaultdict(lambda: defaultdict(int))
            annotated = review_queryset.annotate(
                rounded_rating=Round('rating')
            ).values('source__name', 'rounded_rating').annotate(count=Count('id'))
            for entry in annotated:
                source_name = entry['source__name']
                rounded_rating = entry['rounded_rating']
                if rounded_rating is None: continue
                scale = _rating_scale_for_source(source_name)
                rating_value = int(rounded_rating)
                rating_value = max(1, min(scale, rating_value))
                source_counts[source_name][str(rating_value)] += entry['count']
            return source_counts

        current_counts_map = _aggregate_counts(reviews)
        previous_counts_map = _aggregate_counts(previous_reviews)

        platform_names = sorted(set(list(current_counts_map.keys()) + list(previous_counts_map.keys())))
        max_scale = max([_rating_scale_for_source(name) for name in platform_names]) if platform_names else 5

        overall_current = defaultdict(int)
        overall_previous = defaultdict(int)
        platforms_payload = []

        for platform_name in platform_names:
            scale = _rating_scale_for_source(platform_name)
            labels = [str(i) for i in range(1, scale + 1)]
            current_platform_counts = current_counts_map.get(platform_name, {})
            previous_platform_counts = previous_counts_map.get(platform_name, {})
            current_series = [current_platform_counts.get(label, 0) for label in labels]
            previous_series = [previous_platform_counts.get(label, 0) for label in labels]
            for label in labels:
                overall_current[label] += current_platform_counts.get(label, 0)
                overall_previous[label] += previous_platform_counts.get(label, 0)
            platforms_payload.append({
                'name': platform_name,
                'labels': labels,
                'current_counts': current_series,
                'previous_counts': previous_series,
                'totals': {'current': sum(current_series), 'previous': sum(previous_series)}
            })

        overall_labels = [str(i) for i in range(1, max_scale + 1)]
        overall_current_series = [overall_current.get(label, 0) for label in overall_labels]
        overall_previous_series = [overall_previous.get(label, 0) for label in overall_labels]

        return {
            'current_period': {'start': current_start, 'end': current_end},
            'previous_period': {'start': previous_params.get('start_date'), 'end': previous_params.get('end_date')},
            'overall': {
                'labels': overall_labels,
                'current_counts': overall_current_series,
                'previous_counts': overall_previous_series,
                'totals': {'current': sum(overall_current_series), 'previous': sum(overall_previous_series)}
            },
            'platforms': platforms_payload,
        }

    overall = get_distribution_internal(request)
    by_resort = _get_by_resort_data(request, get_distribution_internal)

    return JsonResponse({
        'overall': overall,
        'by_resort': by_resort
    })
