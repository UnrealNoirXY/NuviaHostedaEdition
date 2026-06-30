from django.core.management.base import BaseCommand
from resort.models import Resort

class Command(BaseCommand):
    help = 'Populates the database with the initial list of resorts.'

    RESORT_NAMES = [
        "Amasea Resort",
        "Suneva Wellness & Golf",
        "CostaRey wellness & Spa",
        "Sunset Village",
        "Zanzibar Village"
    ]

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting to populate resorts..."))

        created_count = 0
        for name in self.RESORT_NAMES:
            resort, created = Resort.objects.get_or_create(name=name)
            if created:
                self.stdout.write(f"  - Created: {resort.name}")
                created_count += 1
            else:
                self.stdout.write(f"  - Already exists: {resort.name}")

        self.stdout.write(self.style.SUCCESS(f"\nPopulation complete. Added {created_count} new resorts."))
