from django.db import migrations

def create_google_source(apps, schema_editor):
    ReviewSource = apps.get_model('reviews', 'ReviewSource')
    ReviewSource.objects.update_or_create(
        name='Google Maps',
        defaults={
            'base_url': 'https://www.google.com/maps',
            'scraper_identifier': 'Xb8osYTtOjlsgI6k9'
        }
    )

class Migration(migrations.Migration):

    dependencies = [
        ('reviews', '0006_update_booking_scraper_id'),
    ]

    operations = [
        migrations.RunPython(create_google_source),
    ]
