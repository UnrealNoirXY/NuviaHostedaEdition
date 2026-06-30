from django.db import migrations

def update_booking_scraper_id(apps, schema_editor):
    ReviewSource = apps.get_model('reviews', 'ReviewSource')
    try:
        booking_source = ReviewSource.objects.get(name='Booking.com')
        booking_source.scraper_identifier = 'PbMHke3jW25J6hSOA'
        booking_source.save()
    except ReviewSource.DoesNotExist:
        # If the source doesn't exist for some reason, we can't update it.
        # This migration will just do nothing in that case.
        pass

class Migration(migrations.Migration):

    dependencies = [
        ('reviews', '0005_populate_booking_source'),
    ]

    operations = [
        migrations.RunPython(update_booking_scraper_id),
    ]
