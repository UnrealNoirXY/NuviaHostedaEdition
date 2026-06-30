import logging
import json
from django.conf import settings
from textblob import TextBlob
from deep_translator import GoogleTranslator

from .models import ScrapingLink, ScrapedData, CompetitorDataAnalysis
from reviews.apify_client import ApifyClientWrapper
from reviews.services import _parse_review_date, _get_tripadvisor_id_from_url

logger = logging.getLogger(__name__)

def analyze_competitor_data(scraped_data: ScrapedData):
    """
    Performs sentiment analysis on a ScrapedData object.
    """
    if not scraped_data.text:
        return

    sentiment_label = 'neutral'
    if scraped_data.rating is not None:
        if scraped_data.rating >= 4.0:
            sentiment_label = 'positive'
        elif scraped_data.rating <= 2.0:
            sentiment_label = 'negative'

    if sentiment_label == 'neutral' or len(scraped_data.text) > 20:
        try:
            translated_text = GoogleTranslator(source='auto', target='en').translate(scraped_data.text)
            blob = TextBlob(translated_text)
            sentiment_score = blob.sentiment.polarity
            if sentiment_score > 0.15: sentiment_label = 'positive'
            elif sentiment_score < -0.15: sentiment_label = 'negative'
            else: sentiment_label = 'neutral'
        except Exception as e:
            logger.error(f"Could not perform sentiment analysis for ScrapedData {scraped_data.id}: {e}")
            sentiment_label = 'neutral'

    if sentiment_label == 'positive': final_score = 0.8
    elif sentiment_label == 'negative': final_score = -0.8
    else: final_score = 0.0

    CompetitorDataAnalysis.objects.update_or_create(
        scraped_data=scraped_data,
        defaults={'sentiment_score': final_score, 'sentiment_label': sentiment_label}
    )
    logger.info(f"Analyzed competitor data {scraped_data.id}: Label={sentiment_label}, Score={final_score:.2f}")

def _save_competitor_results(results: list, scraping_link: ScrapingLink):
    """
    Parses and saves the data scraped from a competitor link, with platform-specific logic.
    """
    new_items_count, skipped_count = 0, 0
    source = scraping_link.source
    for item in results:
        if isinstance(item, str):
            try:
                item = json.loads(item)
            except json.JSONDecodeError:
                continue

        source_identifier, author_name, rating, title, text, publication_date_str = (None, 'Anonimo', None, '', '', None)

        if source.name == 'Tripadvisor':
            source_identifier, author_name, rating, title, text, publication_date_str = (item.get('id'), item.get('author', {}).get('name') or 'Anonimo', item.get('rating'), item.get('title', ''), item.get('text', ''), item.get('publishedDate'))
        elif source.name == 'Booking.com':
            source_identifier, author_name, rating, title, publication_date_str = (item.get('id'), item.get('userName') or 'Anonimo', item.get('rating'), item.get('reviewTitle', ''), item.get('reviewDate'))
            liked, disliked = (item.get('likedText') or '').strip(), (item.get('dislikedText') or '').strip()
            text = f"Liked: {liked}\nDisliked: {disliked}".strip()
        elif source.name == 'Google Maps':
            source_identifier, author_name, rating, title, text, publication_date_str = (item.get('reviewId'), item.get('name') or 'Anonimo', item.get('stars'), item.get('title', ''), item.get('text', ''), item.get('publishedAtDate'))

        if not source_identifier or ScrapedData.objects.filter(scraping_link=scraping_link, source_identifier=str(source_identifier)).exists():
            skipped_count += 1
            continue

        try:
            ScrapedData.objects.create(
                scraping_link=scraping_link, source_identifier=str(source_identifier), data_type='review',
                title=title, text=text, rating=rating, author=author_name,
                publication_date=_parse_review_date(publication_date_str), raw_data=item
            )
            new_items_count += 1
        except Exception as e:
            logger.error(f"Error saving scraped data for link {scraping_link.id}: {e}", exc_info=True)
            skipped_count += 1
    logger.info(f"Source: {source.name} | Saved: {new_items_count} | Skipped: {skipped_count}")
    return {'saved': new_items_count, 'skipped': skipped_count}

def trigger_competitor_scraping(scraping_link_ids: list = None):
    """
    Triggers the scraping process for specified competitor links.
    """
    api_token = settings.APIFY_API_TOKEN
    if not api_token:
        logger.error("APIFY_API_TOKEN is not configured.")
        raise ValueError('APIFY_API_TOKEN is not configured in settings.')
    client = ApifyClientWrapper(api_token)
    summary = {}
    links_to_scrape = ScrapingLink.objects.filter(id__in=scraping_link_ids, is_active=True) if scraping_link_ids else ScrapingLink.objects.filter(is_active=True)
    if not links_to_scrape.exists():
        logger.warning("No active scraping links found.")
        return {}
    links_by_source = {}
    for link in links_to_scrape:
        if link.source.scraper_identifier not in links_by_source:
            links_by_source[link.source.scraper_identifier] = {'source': link.source, 'links': []}
        links_by_source[link.source.scraper_identifier]['links'].append(link)
    for scraper_identifier, data in links_by_source.items():
        source, links = data['source'], data['links']
        start_urls = [{"url": link.url} for link in links]
        run_input = links[0].platform_options.copy()
        run_input['startUrls'] = start_urls
        logger.info(f"Starting scraper '{scraper_identifier}' for source '{source.name}' with {len(start_urls)} URLs.")
        try:
            run = client.start_scraper(scraper_identifier, run_input)
            results = client.get_run_results(run)
            for link in links:
                summary[f"{link.id}:{link.competitor.name}"] = _save_competitor_results(results, link)
        except Exception as e:
            logger.error(f"An error occurred while running scraper for '{source.name}': {e}", exc_info=True)
            summary[source.name] = {'error': str(e)}
    return summary
