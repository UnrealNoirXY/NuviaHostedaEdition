from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Avg, Count, Q, F, Case, When, FloatField
from django.db.models.functions import Coalesce, TruncMonth
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib import messages
from django.urls import reverse, reverse_lazy
from django.http import HttpResponse
import csv
import io
import base64
import matplotlib.pyplot as plt
from weasyprint import HTML
from datetime import datetime
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.core.paginator import Paginator
import json
import re
import types
from collections import Counter
from datetime import timedelta

from .models import Review, ReviewAnalysis, Resort, ScrapingURL, ReviewSource, ReportTemplate, ScheduledScraping
from .forms import (
    ScrapingURLForm, ScrapingTaskForm, RatingReportFilterForm, KeywordAnalysisForm,
    SentimentReportFilterForm, PlatformPerformanceFilterForm, ReportTemplateForm, ScheduledScrapingForm
)
from accounts.models import User
from clients.models import Company
from core.utils import themed_render
from .access import can_access_reviews, scope_reviews
from .pdf_generator import generate_report_pdf
from .veratour_views import veratour_upload_wizard_view, veratour_task_status_api


def _get_analysis_center_filtered_reviews(request):
    user = request.user
    reviews = Review.objects.select_related('analysis', 'source', 'resort').all()

    # Visibilità per ruolo/azienda (fonte di verità: reviews/access.py)
    reviews = scope_reviews(reviews, user)

    # Apply filters from request
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    resort_ids_str = request.GET.get('resorts')
    source_ids_str = request.GET.get('sources')

    if resort_ids_str:
        resort_ids = [int(id) for id in resort_ids_str.split(',')]
        if user.role == User.DIRECTOR:
            if user.resort and user.resort.id in resort_ids:
                 reviews = reviews.filter(resort_id=user.resort.id)
            else:
                 reviews = reviews.none()
        else:
            reviews = reviews.filter(resort_id__in=resort_ids)

    if source_ids_str:
        source_ids = [int(id) for id in source_ids_str.split(',')]
        reviews = reviews.filter(source_id__in=source_ids)

    if start_date_str:
        reviews = reviews.filter(review_date__gte=start_date_str)

    if end_date_str:
        end_date = (
            datetime.strptime(end_date_str, "%Y-%m-%d") + timedelta(days=1)
        ).strftime('%Y-%m-%d')
        reviews = reviews.filter(review_date__lt=end_date)

    return reviews

def _get_filtered_reviews(request, form_class):
    user = request.user
    if not can_access_reviews(user):
        messages.error(request, "Non hai il permesso di accedere a questa sezione.")
        return None, None

    reviews = Review.objects.select_related('analysis', 'source', 'resort').all()

    # Visibilità per ruolo/azienda (fonte di verità: reviews/access.py)
    reviews = scope_reviews(reviews, user)
    form = form_class(request.GET or None, user=user)
    if form.is_valid():
        if form.cleaned_data.get('company'):
            reviews = reviews.filter(resort__company=form.cleaned_data['company'])
        if form.cleaned_data.get('resort'):
            reviews = reviews.filter(resort=form.cleaned_data['resort'])
        if form.cleaned_data.get('start_date'):
            reviews = reviews.filter(review_date__gte=form.cleaned_data['start_date'])
        if form.cleaned_data.get('end_date'):
            end_date = form.cleaned_data['end_date'] + timedelta(days=1)
            reviews = reviews.filter(review_date__lt=end_date)
        if form.cleaned_data.get('sources'):
            reviews = reviews.filter(source__in=form.cleaned_data['sources'])
    return reviews, form

@login_required
def review_dashboard_view(request):
    user = request.user
    if not can_access_reviews(user):
        messages.error(request, "Non hai il permesso di accedere a questa sezione.")
        return redirect('home')

    # Base queryset with rating normalization
    normalized_rating = Case(
        When(source__name='Booking.com', then=F('rating') / 2),
        default=F('rating'),
        output_field=FloatField()
    )
    review_queryset = Review.objects.all()

    resort_queryset = Resort.objects.all()
    companies = Company.objects.all() if user.is_superuser else None
    selected_company = None

    if user.is_superuser:
        company_id = request.GET.get('company_id')
        if company_id:
            selected_company = get_object_or_404(Company, pk=company_id)
            review_queryset = review_queryset.filter(resort__company=selected_company)
            resort_queryset = resort_queryset.filter(company=selected_company)
    elif user.role in [User.OWNER, User.CORPORATE, User.RISORSE_UMANE, User.CAPO_ECONOMO, User.HEAD_MAINTAINER]:
        selected_company = user.company
        if selected_company:
            review_queryset = review_queryset.filter(resort__company=selected_company)
            resort_queryset = resort_queryset.filter(company=selected_company)
        else:
            review_queryset = review_queryset.none()
            resort_queryset = Resort.objects.none()
    elif user.role == User.DIRECTOR:
        if user.resort:
            review_queryset = review_queryset.filter(resort=user.resort)
            resort_queryset = resort_queryset.filter(pk=user.resort.pk)
            selected_company = user.resort.company
        else:
            review_queryset = review_queryset.none()
            resort_queryset = Resort.objects.none()

    selected_resort = None
    resort_id = request.GET.get('resort_id')
    if resort_id:
        if user.role != User.DIRECTOR:
            query_params = {'pk': resort_id}
            if selected_company:
                query_params['company'] = selected_company
            selected_resort = get_object_or_404(Resort, **query_params)
            review_queryset = review_queryset.filter(resort=selected_resort)
        elif user.resort and int(resort_id) == user.resort.pk:
            selected_resort = user.resort
    all_sources = ReviewSource.objects.all()
    selected_source = None
    source_id = request.GET.get('source_id')
    if source_id:
        selected_source = get_object_or_404(ReviewSource, pk=source_id)
        review_queryset = review_queryset.filter(source=selected_source)

    start_date_str = request.GET.get('start_date')
    if start_date_str:
        review_queryset = review_queryset.filter(review_date__gte=start_date_str)

    end_date_str = request.GET.get('end_date')
    if end_date_str:
        review_queryset = review_queryset.filter(review_date__lte=end_date_str)

    total_reviews = review_queryset.count()

    average_rating = 0
    rating_scale = 5
    show_rating_normalization_info = False

    if selected_source:
        if selected_source.name == 'Booking.com':
            rating_scale = 10
        average_rating = review_queryset.aggregate(avg_rating=Coalesce(Avg('rating'), 0.0))['avg_rating']
    else:
        show_rating_normalization_info = True
        normalized_rating_qs = review_queryset.annotate(
            normalized_rating=Case(
                When(source__name='Booking.com', then=F('rating') / 2),
                default=F('rating'),
                output_field=FloatField()
            )
        )
        average_rating = normalized_rating_qs.aggregate(avg_rating=Coalesce(Avg('normalized_rating'), 0.0))['avg_rating']

    sentiment_counts = ReviewAnalysis.objects.filter(review__in=review_queryset).values('sentiment_label').annotate(count=Count('id'))
    sentiment_data = {item['sentiment_label']: item['count'] for item in sentiment_counts}
    sentiment_breakdown = {
        'positive': sentiment_data.get('positive', 0),
        'neutral': sentiment_data.get('neutral', 0),
        'negative': sentiment_data.get('negative', 0),
    }

    # --- Ratings by source ---
    ratings_by_source_qs = review_queryset.annotate(
        normalized_rating=Case(
            When(source__name='Booking.com', then=F('rating') / 2),
            default=F('rating'),
            output_field=FloatField()
        )
    ).values('source__name').annotate(
        avg_rating=Avg('normalized_rating')
    ).order_by('-avg_rating')

    ratings_by_source = {
        item['source__name']: round(item['avg_rating'], 2) for item in ratings_by_source_qs if item['avg_rating']
    }

    reviews_for_display = None
    is_grouped = False
    if not selected_resort and not selected_source:
        is_grouped = True
        grouped_reviews = {}
        reviews = review_queryset.select_related('resort', 'source', 'analysis').order_by('source__name', '-review_date')
        for review in reviews:
            if review.source.name not in grouped_reviews:
                grouped_reviews[review.source.name] = []
            grouped_reviews[review.source.name].append(review)
        reviews_for_display = grouped_reviews
    else:
        reviews_for_display = review_queryset.select_related('resort', 'source', 'analysis').order_by('-review_date')[:20]
    context = {
        'total_reviews': total_reviews,
        'average_rating': average_rating,
        'rating_scale': rating_scale,
        'show_rating_normalization_info': show_rating_normalization_info,
        'sentiment_breakdown': sentiment_breakdown,
        'ratings_by_source': ratings_by_source,
        'reviews_for_display': reviews_for_display,
        'is_grouped': is_grouped,
        'companies': companies,
        'selected_company': selected_company,
        'all_resorts': resort_queryset.order_by('name'),
        'selected_resort': selected_resort,
        'all_sources': all_sources,
        'selected_source': selected_source,
        'page_title': 'Review Analysis Dashboard'
    }
    return themed_render(request, 'reviews/dashboard.html', context)

@login_required
def manage_scraping_urls(request, resort_id):
    # This view remains unchanged
    resort = get_object_or_404(Resort, pk=resort_id)
    user = request.user
    can_manage = user.is_superuser or (user.role == User.OWNER and resort.company == user.company)
    if not can_manage:
        messages.error(request, "Non hai il permesso di gestire gli URL per questo resort.")
        return redirect('core:resort_list')
    if request.method == 'POST':
        form = ScrapingURLForm(request.POST)
        if form.is_valid():
            new_url = form.save(commit=False)
            new_url.resort = resort
            try:
                new_url.save()
                messages.success(request, "URL di scraping aggiunto con successo.")
            except IntegrityError:
                messages.error(request, "Un URL per questa fonte e resort esiste già.")
            return redirect('reviews:manage_scraping_urls', resort_id=resort.id)
    else:
        form = ScrapingURLForm()
        form.fields['source'].queryset = ReviewSource.objects.all()
    scraping_urls = resort.scraping_urls.all().select_related('source')
    context = {'resort': resort, 'scraping_urls': scraping_urls, 'form': form}
    return themed_render(request, 'reviews/manage_urls.html', context)

@login_required
def delete_scraping_url(request, pk):
    # This view remains unchanged
    scraping_url = get_object_or_404(ScrapingURL, pk=pk)
    resort = scraping_url.resort
    user = request.user
    can_manage = user.is_superuser or (user.role == User.OWNER and resort.company == user.company)
    if not can_manage:
        messages.error(request, "Non hai il permesso di eliminare questo URL.")
        return redirect('core:resort_list')
    if request.method == 'POST':
        scraping_url.delete()
        messages.success(request, "URL di scraping eliminato con successo.")
        return redirect('reviews:manage_scraping_urls', resort_id=resort.id)
    messages.error(request, "Richiesta non valida.")
    return redirect('reviews:manage_scraping_urls', resort_id=resort.id)

def review_detail_view(request, pk):
    try:
        review = Review.objects.select_related('resort__company', 'source', 'analysis').get(pk=pk)
    except Review.DoesNotExist:
        messages.error(request, "Recensione non trovata.")
        return redirect('reviews:dashboard')

    # If user is not authenticated, show a public, minimal version of the page.
    if not request.user.is_authenticated:
        return render(request, 'reviews/public_review_detail.html', {'review': review})

    # If user is authenticated, check their permissions to see the full internal view.
    user = request.user
    can_view = False
    if user.is_superuser:
        can_view = True
    elif user.role in [User.OWNER, User.CORPORATE, User.RISORSE_UMANE, User.CAPO_ECONOMO, User.HEAD_MAINTAINER] and user.company and review.resort.company == user.company:
        can_view = True
    elif user.role == User.DIRECTOR and user.resort and review.resort == user.resort:
        can_view = True

    if not can_view:
        messages.error(request, "Non hai il permesso di visualizzare questa recensione.")
        return redirect('reviews:dashboard')

    context = {'review': review, 'page_title': f'Dettaglio Recensione: {review.title}'}
    return themed_render(request, 'reviews/review_detail.html', context)

@login_required
def scraping_panel_view(request):
    user = request.user
    # Solo i superadmin possono accedere a questa funzione.
    if user.role != User.SUPERADMIN:
        messages.error(request, "Non hai il permesso di accedere a questa sezione.")
        return redirect('home')

    if request.method == 'POST':
        form = ScrapingTaskForm(request.POST, user=user)
        if form.is_valid():
            from .services import trigger_review_scraping

            resort_ids = list(form.cleaned_data['resorts'].values_list('id', flat=True))
            sources_to_scrape = form.cleaned_data['sources']

            summary = trigger_review_scraping(
                resort_ids=resort_ids,
                start_date=form.cleaned_data.get('start_date'),
                sources_to_scrape=sources_to_scrape,
                max_reviews_per_hotel=form.cleaned_data.get('max_reviews_booking'),
                max_reviews_google=form.cleaned_data.get('max_reviews_google'),
                max_reviews_tripadvisor=form.cleaned_data.get('max_reviews_tripadvisor')
            )

            summary_parts = []
            for source, result in summary.items():
                if 'error' in result:
                    summary_parts.append(f"{source}: Errore ({result['error']})")
                else:
                    summary_parts.append(f"{source}: {result.get('saved', 0)} salvate, {result.get('skipped', 0)} saltate")

            if summary_parts:
                messages.success(request, f"Scraping completato. Risultati: {'; '.join(summary_parts)}.")
            else:
                messages.warning(request, "Nessuna fonte di scraping trovata per i resort selezionati.")

            return redirect('reviews:scraping_panel')
    else:
        form = ScrapingTaskForm(user=user)

    context = {'form': form, 'page_title': 'Pannello di Scraping Manuale'}
    return themed_render(request, 'reviews/scraping_panel.html', context)

@login_required
def review_list_view(request):
    user = request.user
    if not can_access_reviews(user):
        messages.error(request, "Non hai il permesso di accedere a questa sezione.")
        return redirect('home')

    review_queryset = Review.objects.select_related('resort', 'source', 'analysis')
    resort_queryset = Resort.objects.all()
    companies = Company.objects.all() if user.is_superuser else None
    selected_company = None

    if user.is_superuser:
        company_id = request.GET.get('company_id')
        if company_id:
            selected_company = get_object_or_404(Company, pk=company_id)
            review_queryset = review_queryset.filter(resort__company=selected_company)
    elif user.role in [User.OWNER, User.CORPORATE, User.RISORSE_UMANE, User.CAPO_ECONOMO, User.HEAD_MAINTAINER]:
        selected_company = user.company
        if selected_company:
            review_queryset = review_queryset.filter(resort__company=selected_company)
        else:
            review_queryset = review_queryset.none()
    elif user.role == User.DIRECTOR:
        if user.resort:
            review_queryset = review_queryset.filter(resort=user.resort)
            selected_company = user.resort.company
        else:
            review_queryset = review_queryset.none()
    if selected_company:
        resort_queryset = resort_queryset.filter(company=selected_company)
    elif user.role == User.DIRECTOR and user.resort:
        resort_queryset = resort_queryset.filter(pk=user.resort.pk)
    selected_resort = None
    resort_id = request.GET.get('resort_id')
    if resort_id:
        # If the user is a director, we must IGNORE the resort_id parameter
        # because their view is already locked to their resort.
        if user.role != User.DIRECTOR:
            query_params = {'pk': resort_id}
            if selected_company:
                query_params['company'] = selected_company
            selected_resort = get_object_or_404(Resort, **query_params)
            review_queryset = review_queryset.filter(resort=selected_resort)
        elif user.resort and int(resort_id) == user.resort.pk:
            # For a director, selected_resort is always their own resort.
            # The queryset is already filtered, this is for context.
            selected_resort = user.resort
    all_sources = ReviewSource.objects.all()
    selected_source = None
    source_id = request.GET.get('source_id')
    if source_id:
        selected_source = get_object_or_404(ReviewSource, pk=source_id)
        review_queryset = review_queryset.filter(source=selected_source)
    search_query = request.GET.get('q', '')
    if search_query:
        review_queryset = review_queryset.filter(Q(title__icontains=search_query) | Q(text__icontains=search_query))
    review_queryset = review_queryset.order_by('-review_date')
    paginator = Paginator(review_queryset, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {
        'page_obj': page_obj, 'companies': companies, 'selected_company': selected_company,
        'all_resorts': resort_queryset.order_by('name'), 'selected_resort': selected_resort,
        'all_sources': all_sources, 'selected_source': selected_source,
        'search_query': search_query, 'page_title': 'Tutte le Recensioni'
    }

    if request.htmx:
        return render(request, 'reviews/partials/_review_list_content.html', context)

    return themed_render(request, 'reviews/review_list.html', context)


@login_required
def test_pdf_report_view(request):
    if not request.user.is_superuser:
        return HttpResponse("Unauthorized", status=403)

    from types import SimpleNamespace
    test_template_obj = SimpleNamespace(
        name="Test Report In-Memory",
        get_report_type_display=lambda: "Analisi Singola",
        filters={'sentiments': ['negative', 'neutral']},
        widgets=['sentiment_chart', 'negative_reviews_list']
    )

    pdf_file = generate_report_pdf(test_template_obj, settings.BASE_URL)
    if pdf_file:
        return HttpResponse(pdf_file, content_type='application/pdf')
    else:
        return HttpResponse("Failed to generate PDF.", status=500)

@login_required
def report_builder_view(request):
    if not request.user.can_export_review_reports:
        messages.error(request, "Non hai il permesso di accedere a questa funzione.")
        return redirect('home')

    if request.method == 'POST':
        form = ReportTemplateForm(request.POST, user=request.user)
        if form.is_valid():

            filters = {}
            if form.cleaned_data.get('resorts'):
                filters['resorts'] = list(form.cleaned_data['resorts'].values_list('id', flat=True))
            if form.cleaned_data.get('sources'):
                filters['sources'] = list(form.cleaned_data['sources'].values_list('id', flat=True))
            if form.cleaned_data.get('sentiments'):
                filters['sentiments'] = form.cleaned_data['sentiments']
            if form.cleaned_data.get('start_date'):
                filters['start_date'] = form.cleaned_data['start_date'].isoformat()
            if form.cleaned_data.get('end_date'):
                filters['end_date'] = form.cleaned_data['end_date'].isoformat()

            action = request.POST.get('action')
            if action == 'generate_pdf':
                from types import SimpleNamespace
                temp_template_obj = SimpleNamespace(
                    name=form.cleaned_data['name'] or "Report Istantaneo",
                    get_report_type_display=lambda: dict(ReportTemplate.REPORT_TYPE_CHOICES).get(form.cleaned_data['report_type']),
                    filters=filters,
                    widgets=form.cleaned_data['widgets']
                )
                pdf_file = generate_report_pdf(temp_template_obj, settings.BASE_URL)
                if pdf_file:
                    response = HttpResponse(pdf_file, content_type='application/pdf')
                    response['Content-Disposition'] = f'attachment; filename="report.pdf"'
                    return response
                else:
                    messages.error(request, "Impossibile generare il PDF.")
                    return redirect('reviews:report_builder')

            elif action == 'save_template':
                template = ReportTemplate(
                    name=form.cleaned_data['name'],
                    user=request.user,
                    report_type=form.cleaned_data['report_type'],
                    widgets=form.cleaned_data['widgets'],
                    filters=filters
                )
                template.save()
                messages.success(request, f"Template '{template.name}' salvato con successo.")
                return redirect('reviews:report_builder')
    else:
        form = ReportTemplateForm(user=request.user)

    templates = ReportTemplate.objects.filter(user=request.user)
    context = {
        'form': form,
        'templates': templates,
        'page_title': "Generatore di Report PDF"
    }
    return themed_render(request, 'reviews/report_builder.html', context)

@login_required
def report_template_delete_view(request, pk):
    template = get_object_or_404(ReportTemplate, pk=pk)

    if not (request.user.is_superuser or template.user == request.user):
        messages.error(request, "Non hai il permesso di eliminare questo template.")
        return redirect('reviews:report_builder')

    if request.method == 'POST':
        template_name = template.name
        template.delete()
        messages.success(request, f"Template '{template_name}' eliminato con successo.")
    else:
        messages.warning(request, "Azione non permessa.")

    return redirect('reviews:report_builder')

@login_required
def report_template_edit_view(request, pk):
    template = get_object_or_404(ReportTemplate, pk=pk)

    if not (request.user.is_superuser or template.user == request.user):
        messages.error(request, "Non hai il permesso di modificare questo template.")
        return redirect('reviews:report_builder')

    if request.method == 'POST':
        form = ReportTemplateForm(request.POST, user=request.user)
        if form.is_valid():
            template.name = form.cleaned_data['name']
            template.report_type = form.cleaned_data['report_type']
            template.widgets = form.cleaned_data['widgets']
            filters = {}
            if form.cleaned_data.get('resorts'):
                filters['resorts'] = list(form.cleaned_data['resorts'].values_list('id', flat=True))
            if form.cleaned_data.get('sources'):
                filters['sources'] = list(form.cleaned_data['sources'].values_list('id', flat=True))
            if form.cleaned_data.get('sentiments'):
                filters['sentiments'] = form.cleaned_data['sentiments']
            if form.cleaned_data.get('start_date'):
                filters['start_date'] = form.cleaned_data['start_date'].isoformat()
            if form.cleaned_data.get('end_date'):
                filters['end_date'] = form.cleaned_data['end_date'].isoformat()
            template.filters = filters
            template.save()
            messages.success(request, f"Template '{template.name}' aggiornato con successo.")
            return redirect('reviews:report_builder')
    else:
        initial_data = {
            'name': template.name,
            'report_type': template.report_type,
            'widgets': template.widgets,
            **template.filters
        }
        form = ReportTemplateForm(initial=initial_data, user=request.user)

    context = {
        'form': form,
        'template_instance': template,
        'page_title': f"Modifica Template: {template.name}"
    }
    return themed_render(request, 'reviews/report_builder.html', context)


@login_required
def export_analysis_csv(request):
    reviews = _get_analysis_center_filtered_reviews(request)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="analysis_export.csv"'

    writer = csv.writer(response)
    writer.writerow(['ID', 'Author', 'Rating', 'Review Date', 'Text', 'Source', 'Resort'])

    for review in reviews:
        writer.writerow([
            review.id,
            review.author,
            review.rating,
            review.review_date.strftime('%Y-%m-%d'),
            review.text,
            review.source.name,
            review.resort.name
        ])

    return response


from django.views.decorators.csrf import csrf_exempt
import json

@csrf_exempt
@login_required
def export_analysis_pdf(request):
    if request.method != 'POST':
        return HttpResponse("This endpoint only accepts POST requests.", status=405)

    data = json.loads(request.body)
    trend_chart_img = data.get('trendChartImg')
    platform_chart_img = data.get('platformChartImg')
    rating_distribution_chart_img = data.get('ratingDistributionChartImg')
    thematic_chart_img = data.get('thematicChartImg')
    kpi_summary = data.get('kpiSummary')

    # We still need to fetch the reviews for the table
    reviews = _get_analysis_center_filtered_reviews(request)

    context = {
        'kpi_summary': kpi_summary,
        'trend_chart_img': trend_chart_img,
        'platform_chart_img': platform_chart_img,
        'rating_distribution_chart_img': rating_distribution_chart_img,
        'thematic_chart_img': thematic_chart_img,
        'reviews': reviews[:50], # Limit reviews for PDF size
        'report_date': datetime.now().strftime('%d/%m/%Y'),
    }

    html_string = render_to_string('reviews/analysis_center_pdf.html', context)
    pdf_file = HTML(string=html_string, base_url=request.build_absolute_uri()).write_pdf()

    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="analysis_report.pdf"'
    return response


# @login_required
def analysis_center_view(request):
    """
    Renders the main page for the Analysis Center, which will host the React app.
    """
    companies = Company.objects.all()
    resorts = Resort.objects.all()
    sources = ReviewSource.objects.all()

    context = {
        'page_title': 'Centro di Analisi Report',
        'filters_data': json.dumps({
            'companies': [{'id': c.id, 'name': c.name} for c in companies],
            'resorts': [{'id': r.id, 'name': r.name} for r in resorts],
            'sources': [{'id': s.id, 'name': s.name} for s in sources],
        })
    }
    return themed_render(request, 'reviews/analysis_center.html', context)


# --- Scheduled Scraping Views ---

class SuperuserRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_superuser

class ScheduledScrapingListView(SuperuserRequiredMixin, ListView):
    model = ScheduledScraping
    template_name = 'reviews/scheduled_scraping_list.html'
    context_object_name = 'tasks'
    paginate_by = 15

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = "Scraping Programmati"
        return context

class ScheduledScrapingCreateView(SuperuserRequiredMixin, CreateView):
    model = ScheduledScraping
    form_class = ScheduledScrapingForm
    template_name = 'reviews/scheduled_scraping_form.html'
    success_url = reverse_lazy('reviews:scheduled_scraping_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = "Crea Nuova Programmazione Scraping"
        return context

    def form_valid(self, form):
        messages.success(self.request, "Programmazione scraping creata con successo.")
        return super().form_valid(form)

class ScheduledScrapingUpdateView(SuperuserRequiredMixin, UpdateView):
    model = ScheduledScraping
    form_class = ScheduledScrapingForm
    template_name = 'reviews/scheduled_scraping_form.html'
    success_url = reverse_lazy('reviews:scheduled_scraping_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = f"Modifica Programmazione: {self.object.name}"
        return context

    def form_valid(self, form):
        messages.success(self.request, "Programmazione scraping aggiornata con successo.")
        return super().form_valid(form)

class ScheduledScrapingDeleteView(SuperuserRequiredMixin, DeleteView):
    model = ScheduledScraping
    template_name = 'reviews/scheduled_scraping_confirm_delete.html'
    success_url = reverse_lazy('reviews:scheduled_scraping_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = f"Elimina Programmazione: {self.object.name}"
        return context

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.object.periodic_task:
            self.object.periodic_task.delete()
        messages.success(self.request, f"Programmazione '{self.object.name}' eliminata con successo.")
        return super().delete(request, *args, **kwargs)
