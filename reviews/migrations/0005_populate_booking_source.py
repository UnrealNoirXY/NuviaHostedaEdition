from django.db import migrations

def create_booking_source(apps, schema_editor):
    ReviewSource = apps.get_model('reviews', 'ReviewSource')
    ReviewSource.objects.update_or_create(
        name='Booking.com',
        defaults={
            'base_url': 'https://www.booking.com',
            'scraper_identifier': 'voyager/booking-reviews-scraper'
        }
    )

class Migration(migrations.Migration):

    dependencies = [
        ('reviews', '0004_update_tripadvisor_scraper_id'),
    ]

    operations = [
        migrations.RunPython(create_booking_source),
    ]
