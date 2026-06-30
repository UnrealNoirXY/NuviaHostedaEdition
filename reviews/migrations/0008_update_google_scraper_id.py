from django.db import migrations

def update_google_scraper_id(apps, schema_editor):
    ReviewSource = apps.get_model('reviews', 'ReviewSource')
    try:
        google_source = ReviewSource.objects.get(name='Google Maps')
        google_source.scraper_identifier = 'compass/Google-Maps-Reviews-Scraper'
        google_source.save()
    except ReviewSource.DoesNotExist:
        pass

class Migration(migrations.Migration):

    dependencies = [
        ('reviews', '0007_populate_google_source'),
    ]

    operations = [
        migrations.RunPython(update_google_scraper_id),
    ]
