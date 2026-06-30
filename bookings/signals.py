from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import GuestDocument
from .tasks import scan_and_ocr_document

@receiver(post_save, sender=GuestDocument)
def queue_scan(sender, instance, created, **kwargs):
    """
    Quando un nuovo GuestDocument viene creato, avvia il task Celery
    per la scansione antivirus e l'OCR in background.
    """
    if created:
        if getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False):
            scan_and_ocr_document.apply(args=[instance.id])
        else:
            scan_and_ocr_document.delay(instance.id)