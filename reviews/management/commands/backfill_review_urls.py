from django.core.management.base import BaseCommand
from django.urls import reverse
from django.conf import settings
from django.db.models import Q
from reviews.models import Review

class Command(BaseCommand):
    help = 'Backfills the original_url field for existing reviews with the absolute public detail view URL.'

    def handle(self, *args, **options):
        self.stdout.write('Searching for reviews with missing or relative URLs...')

        reviews_to_update = Review.objects.filter(
            Q(original_url__isnull=True) | Q(original_url='') | Q(original_url__startswith='/')
        )
        count = reviews_to_update.count()

        if count == 0:
            self.stdout.write(self.style.SUCCESS('No reviews needed updating.'))
            return

        self.stdout.write(f'Found {count} reviews to update.')

        base_url = settings.BASE_URL.rstrip('/')

        updated_reviews = []
        for review in reviews_to_update:
            relative_path = reverse('reviews:review_detail', kwargs={'pk': review.pk})
            review.original_url = f"{base_url}{relative_path}"
            updated_reviews.append(review)

        Review.objects.bulk_update(updated_reviews, ['original_url'])

        self.stdout.write(self.style.SUCCESS(f'Successfully updated {count} reviews.'))
