import io
import base64
from django.db.models import Q
from django.template.loader import render_to_string
from django.urls import reverse
from weasyprint import HTML
from datetime import date

from .models import Review
from clients.models import Company
from resort.models import Resort

def generate_report_pdf(template_obj, base_url=None):
    if not template_obj:
        return None

    filters = template_obj.filters
    reviews_qs = Review.objects.select_related('analysis', 'resort__company', 'source').order_by('resort__name', '-review_date')

    # Apply filters
    if filters.get('resorts'):
        reviews_qs = reviews_qs.filter(resort_id__in=filters['resorts'])
    if filters.get('sources'):
        reviews_qs = reviews_qs.filter(source_id__in=filters['sources'])
    if filters.get('sentiments'):
        reviews_qs = reviews_qs.filter(analysis__sentiment_label__in=filters['sentiments'])
    if filters.get('start_date'):
        reviews_qs = reviews_qs.filter(review_date__gte=filters['start_date'])
    if filters.get('end_date'):
        reviews_qs = reviews_qs.filter(review_date__lte=filters['end_date'])

    # Add public URL to each review and strip leading whitespace from review text
    reviews_list = list(reviews_qs)
    for review in reviews_list:
        if review.text:
            review.text = review.text.replace('\u00A0', ' ').lstrip()
        if base_url:
            review.public_url = f"{base_url.rstrip('/')}{reverse('reviews:review_detail', kwargs={'pk': review.pk})}"

    company_logo_url = None
    # Attempt to get a single company from the filters to find the logo
    company = None
    if filters.get('resorts'):
        resort_ids = filters.get('resorts')
        first_resort = Resort.objects.filter(id__in=resort_ids).first()
        if first_resort:
            company = first_resort.company

    if company and company.logo and base_url:
        company_logo_url = f"{base_url.rstrip('/')}{company.logo.url}"

    context = {
        'report_name': template_obj.name,
        'report_date': date.today(),
        'company_logo_url': company_logo_url,
        'total_reviews_found': len(reviews_list),
        'reviews': reviews_list,
    }

    html_string = render_to_string('reviews/pdf_report.html', context)
    pdf_file = HTML(string=html_string).write_pdf()

    return pdf_file
