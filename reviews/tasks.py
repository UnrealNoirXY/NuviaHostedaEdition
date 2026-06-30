from celery import shared_task
from django.utils import timezone
from datetime import timedelta
import logging

from .models import ScheduledScraping, Resort, VeratourReport
from .services import trigger_review_scraping
from .veratour_utils import parse_veratour_report, process_vota_commenti

logger = logging.getLogger(__name__)

@shared_task(bind=True)
def process_veratour_upload_task(self, resort_id, report_file_path, commenti_file_path, max_capacity=None):
    """
    Background task to process Veratour Excel files.
    """
    try:
        resort = Resort.objects.get(pk=resort_id)

        # 1. Process Report (Total Guests)
        self.update_state(state='PROGRESS', meta={'step': 1, 'message': 'Parsing file REPORT...'})
        total_guests, start_date, end_date, report_data = parse_veratour_report(report_file_path, resort)

        if total_guests > 0 and start_date and end_date:
            VeratourReport.objects.update_or_create(
                resort=resort,
                start_date=start_date,
                end_date=end_date,
                defaults={
                    'total_guests': total_guests,
                    'max_capacity': max_capacity,
                    'data': report_data
                }
            )

        # 2. Process Comments
        self.update_state(state='PROGRESS', meta={'step': 2, 'message': 'Parsing file VOTA_COMMENTI e Sentiment Analysis...'})

        def progress_callback(current, total):
            percent = int((current / total) * 100)
            self.update_state(state='PROGRESS', meta={
                'step': 2,
                'message': f'Analisi commenti in corso: {percent}%',
                'percent': percent
            })

        process_vota_commenti(commenti_file_path, resort, progress_callback=progress_callback)

        return {
            'status': 'SUCCESS',
            'message': 'Elaborazione completata con successo.',
            'resort': resort.name,
            'guests': total_guests
        }

    except Exception as e:
        logger.error(f"Error processing Veratour upload: {e}", exc_info=True)
        return {
            'status': 'FAILURE',
            'message': str(e)
        }

@shared_task
def run_scheduled_scraping(scheduled_scraping_id):
    """
    Celery task to run a specific scheduled scraping job.
    """
    try:
        job = ScheduledScraping.objects.get(id=scheduled_scraping_id, is_active=True)
    except ScheduledScraping.DoesNotExist:
        logger.warning(f"ScheduledScraping job with id={scheduled_scraping_id} not found or is inactive. Skipping.")
        return f"Job {scheduled_scraping_id} not found or inactive."

    logger.info(f"Starting scheduled scraping job: '{job.name}' (ID: {job.id})")

    # Determine the start date for fetching reviews
    start_date = None
    if job.scrape_period_days > 0:
        start_date = timezone.now().date() - timedelta(days=job.scrape_period_days)

    # Get the list of resort IDs. If empty, the service will scrape all.
    resort_ids = list(job.resorts.values_list('id', flat=True))

    try:
        summary = trigger_review_scraping(
            resort_ids=resort_ids if resort_ids else None,
            start_date=start_date,
            sources_to_scrape=list(job.sources.all()),
            max_reviews_per_hotel=job.max_reviews_booking,
            max_reviews_google=job.max_reviews_google,
            max_reviews_tripadvisor=job.max_reviews_tripadvisor
        )

        summary_str = "; ".join([f"{source}: {res.get('saved', 0)} saved, {res.get('skipped', 0)} skipped" for source, res in summary.items()])
        logger.info(f"Successfully completed scraping job '{job.name}'. Summary: {summary_str}")
        return f"Job '{job.name}' completed. {summary_str}"

    except Exception as e:
        logger.error(f"An error occurred during scheduled scraping job '{job.name}': {e}", exc_info=True)
        return f"Job '{job.name}' failed with error: {e}"
