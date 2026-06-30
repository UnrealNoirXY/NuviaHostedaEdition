import re
import logging
from django.utils.dateparse import parse_datetime
from django.utils import timezone
from django.conf import settings
from django.db import IntegrityError
from textblob import TextBlob

from .models import Review, ReviewAnalysis, ReviewSource, ScrapingURL
from .apify_client import ApifyClientWrapper
from .veratour_utils import get_sentiment_score_and_label

# Using python's logging for service-level logging
logger = logging.getLogger(__name__)

def _get_tripadvisor_id_from_url(url):
    if not url:
        return None
    match = re.search(r'(g\d+-d\d+)', url)
    return match.group(1) if match else None

def _parse_review_date(date_str: str) -> timezone.datetime:
    if not date_str:
        return timezone.now()
    try:
        from dateutil.parser import parse
        return timezone.make_aware(parse(date_str))
    except (ImportError, ValueError):
        dt = parse_datetime(date_str)
        if dt:
            return dt if timezone.is_aware(dt) else timezone.make_aware(dt)
    logger.warning(f"Could not parse date '{date_str}'. Using current time as fallback.")
    return timezone.now()

def _save_results(results, source, scraping_urls):
    new_reviews_count = 0
    skipped_count = 0
    import json

    resort_map = {}
    # For all sources, the most reliable way is to map the exact scraped URL to the resort
    for s_url in scraping_urls:
        resort_map[s_url.url] = s_url.resort

    for item in results:
        # Safeguard: if the item from the dataset is a string, parse it as JSON
        if isinstance(item, str):
            try:
                item = json.loads(item)
            except json.JSONDecodeError:
                logger.warning(f"Could not parse item from JSON string: {item}")
                continue

        review_id = None
        author_name = 'Anonimo'
        rating = None
        title = ''
        text = ''
        review_date_str = None
        original_url = None

        # --- Adapt parsing based on source ---
        if source.name == 'Tripadvisor':
            review_id = item.get('id')
            author_name = item.get('author', {}).get('name') or 'Anonimo'
            rating = item.get('rating')
            # Normalize TripAdvisor rating if it's on a 10-50 scale (bubbles)
            if rating and rating > 5:
                rating = rating / 10.0
            title = item.get('title') or ''
            text = item.get('text') or ''
            review_date_str = item.get('publishedDate')
            # For Tripadvisor, the resort is mapped via a location ID in the review URL
            review_url = item.get('url')
            location_id = _get_tripadvisor_id_from_url(review_url)
            # We need a different map for tripadvisor, from location_id to resort
            tripadvisor_resort_map = { _get_tripadvisor_id_from_url(s_url.url): s_url.resort for s_url in scraping_urls }
            resort = tripadvisor_resort_map.get(location_id)

        elif source.name == 'Booking.com':
            review_id = item.get('id')
            author_name = item.get('userName') or 'Anonimo'
            rating = item.get('rating')
            title = item.get('reviewTitle') or ''

            liked = (item.get('likedText') or '').strip()
            disliked = (item.get('dislikedText') or '').strip()

            text_parts = []
            if liked:
                text_parts.append(f"Liked: {liked}")
            if disliked:
                text_parts.append(f"Disliked: {disliked}")
            text = "\n".join(text_parts)

            review_date_str = item.get('reviewDate')
            # For Booking, the result contains the URL we used to scrape
            original_url = item.get('startUrl')
            resort = resort_map.get(original_url)

        elif source.name == 'Google Maps':
            review_id = item.get('reviewId')
            author_name = item.get('name') or 'Anonimo'
            rating = item.get('stars')
            title = item.get('title') or '' # Google reviews don't have titles, so this will be blank
            text = item.get('text') or ''
            review_date_str = item.get('publishedAtDate')

            # For Google, the resort is mapped via the original search string URL
            search_string = item.get('searchString', '')
            # The URL is after "Direct Detail URL: "
            if 'Direct Detail URL: ' in search_string:
                original_url = search_string.split('Direct Detail URL: ')[1]
                resort = resort_map.get(original_url)

        if not review_id:
            logger.warning("Skipping item with no review_id.")
            continue

        if not resort:
            logger.warning(f"Could not find a resort for scraped URL '{original_url or 'N/A'}'. Skipping.")
            continue

        if Review.objects.filter(source=source, review_id=str(review_id)).exists():
            skipped_count += 1
            continue

        # Diagnostic log for reviews with rating but no text
        if rating is not None and not text:
            logger.info(f"Review {review_id} from {source.name} has a rating ({rating}) but no text content. Proceeding to save.")

        review_date = _parse_review_date(review_date_str)

        try:
            Review.objects.create(
                source=source,
                resort=resort,
                review_id=str(review_id),
                author=author_name,
                rating=rating,
                title=title,
                text=text,
                review_date=review_date,
            )
            new_reviews_count += 1
        except IntegrityError as e:
            logger.warning(f"Could not save review {review_id} due to integrity error: {e}")
        except Exception as e:
            logger.error(f"An unexpected error occurred while saving review {review_id}: {e}")

    return {'saved': new_reviews_count, 'skipped': skipped_count}


def trigger_review_scraping(resort_ids=None, start_date=None, sources_to_scrape=None, max_reviews_per_hotel=None, max_reviews_google=None, max_reviews_tripadvisor=None):
    """
    Triggers the review scraping process for specified resorts.
    :param resort_ids: A list of resort IDs to scrape. If None, scrapes for all resorts.
    :param start_date: A date object. If provided, tells the scraper to only fetch reviews newer than this date.
    :param sources_to_scrape: A list of ReviewSource objects to scrape. If None, scrapes all available sources.
    :param max_reviews_per_hotel: The maximum number of reviews to fetch for Booking.com.
    :param max_reviews_google: The maximum number of reviews to fetch for Google.
    :param max_reviews_tripadvisor: The maximum number of reviews to fetch for Tripadvisor.
    :return: A dictionary summarizing the results for each source.
    """
    api_token = settings.APIFY_API_TOKEN
    if not api_token:
        raise ValueError('APIFY_API_TOKEN is not configured in settings.')

    client = ApifyClientWrapper(api_token)
    summary = {}

    if sources_to_scrape:
        sources = sources_to_scrape
    else:
        sources = ReviewSource.objects.filter(scraper_identifier__isnull=False).exclude(scraper_identifier__exact='')

    for source in sources:
        logger.info(f"Processing source: {source.name}")

        scraping_urls_qs = ScrapingURL.objects.filter(source=source)
        if resort_ids:
            scraping_urls_qs = scraping_urls_qs.filter(resort_id__in=resort_ids)

        if not scraping_urls_qs.exists():
            logger.warning(f"No scraping URLs found for source '{source.name}' with the given filters. Skipping.")
            continue

        start_urls = [{"url": s_url.url} for s_url in scraping_urls_qs]
        run_input = {}

        # --- Set Input based on Source ---
        if source.name == 'Tripadvisor':
            # This actor sorts by newest reviews by default.
            # 'lastReviewDate' acts as a cutoff for older reviews.
            run_input = {
                "startUrls": start_urls,
                "scrapeReviewerInfo": True,
            }
            if start_date:
                run_input["lastReviewDate"] = start_date.strftime('%Y-%m-%d')
            if max_reviews_tripadvisor:
                run_input['maxReviews'] = int(max_reviews_tripadvisor)

        elif source.name == 'Booking.com':
            run_input = {
                "startUrls": start_urls,
                "sortReviewsBy": "f_recent_desc", # Sort by most recent reviews
                "reviewScores": ["ALL"],
            }
            if max_reviews_per_hotel:
                run_input['maxReviewsPerHotel'] = int(max_reviews_per_hotel)
            if start_date:
                run_input['cutoffDate'] = start_date.strftime('%Y-%m-%d')

        elif source.name == 'Google Maps':
            run_input = {
                "startUrls": start_urls,
                "reviewsSort": "newest",
                "language": "en",
                "reviewsOrigin": "all",
                "personalData": True,
            }
            if max_reviews_google:
                run_input['maxReviews'] = int(max_reviews_google)

        if not run_input:
            logger.warning(f"No run input configuration for source '{source.name}'. Skipping.")
            continue

        try:
            run = client.start_scraper(source.scraper_identifier, run_input)
            results = client.get_run_results(run)
            source_summary = _save_results(results, source, scraping_urls_qs)
            summary[source.name] = source_summary
            logger.info(f"Finished processing for {source.name}. Saved {source_summary['saved']} new reviews, skipped {source_summary['skipped']}.")
        except Exception as e:
            logger.error(f"An error occurred while running scraper for '{source.name}': {e}")
            summary[source.name] = {'error': str(e)}

    return summary


# NOTE: AI pipelines are disabled due to environment constraints (lack of disk space).
# The code remains as a reference for future implementation in a more powerful environment.
topic_classifier = None
text_generator = None


def analyze_review_sentiment(review: Review):
    """
    Performs sentiment and topic analysis on a given Review object and saves the result.
    - It uses a local Italian sentiment model (for Veratour and potentially others).
    - It falls back to rating-based heuristic if necessary.
    """
    # --- Rating-based Sanity Check for Sentiment ---
    normalized_rating = review.rating
    if review.source.name == 'Booking.com':
        normalized_rating = review.rating / 2.0

    if normalized_rating >= 4.5:
        sentiment_label = 'positive'
    elif normalized_rating <= 2.0:
        sentiment_label = 'negative'
    else:
        # --- Text-based analysis for intermediate ratings ---
        if review.text:
            try:
                # Use local sentiment engine
                _, sentiment_label, _ = get_sentiment_score_and_label(review.text)
            except Exception as e:
                logger.error(f"Could not perform sentiment analysis for review {review.id}: {e}")
                sentiment_label = 'neutral'
        else:
            sentiment_label = 'neutral'

    # Assign a final score based on the determined label
    # NOTE: In more recent implementation (Veratour), we use get_sentiment_score_and_label
    # which returns a polarity in the range [-1, 1] and a label.

    # Check for anomalies
    # Anomaly: Report Rating >= 9 and IA Sentiment score <= 3 (on 1-10 scale)
    # The current analyze_review_sentiment is more generic, but we should follow the new requirements.
    # For web reviews (Google, Booking, Tripadvisor), we might need to normalize the rating to 1-10.

    normalized_rating_10 = review.rating
    if review.source.name == 'Booking.com':
        normalized_rating_10 = review.rating # Booking is already 1-10
    elif review.source.name in ['Google Maps', 'Tripadvisor']:
        normalized_rating_10 = review.rating * 2 # 1-5 to 1-10

    ia_score, ia_label, ia_polarity = 6, 'neutral', 0.0
    if review.text:
        try:
            ia_score, ia_label, ia_polarity = get_sentiment_score_and_label(review.text)
        except Exception as e:
            logger.error(f"Sentiment analysis error for review {review.id}: {e}")

    is_anomaly = (normalized_rating_10 >= 9 and ia_score <= 3)

    ReviewAnalysis.objects.update_or_create(
        review=review,
        defaults={
            'sentiment_score': ia_polarity,
            'sentiment_label': ia_label,
            'keywords': [], # Reset keywords or update if needed
            'is_anomaly': is_anomaly,
        }
    )

    print(f"Analyzed review {review.id}: Rating={normalized_rating_10:.1f}, Label={ia_label}, Score={ia_polarity:.2f}, Anomaly={is_anomaly}")


def generate_review_reply(review: Review):
    """
    Generates a suggested reply for a given review.
    NOTE: This feature is currently disabled due to environment constraints.
    It returns an empty string.
    """
    return ""
