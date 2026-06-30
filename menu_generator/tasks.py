import logging

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.utils import timezone
from celery import shared_task

from .documents import build_cavalieri_docx, build_menu_bundle, build_menu_docx, build_menu_pdf
from .models import MenuDocumentJob

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def generate_menu_documents_task(self, job_id: str):
    try:
        job = MenuDocumentJob.objects.select_related("menu").get(id=job_id)
    except MenuDocumentJob.DoesNotExist:
        return f"MenuDocumentJob {job_id} non trovato"

    job.status = MenuDocumentJob.STATUS_RUNNING
    job.progress = 10
    job.save(update_fields=["status", "progress", "updated_at"])

    try:
        menu = job.menu
        if job.output_format == "pdf":
            content, filename = build_menu_pdf(menu, doc_type=job.doc_type)
            content_file = ContentFile(content)
        elif job.output_format == "docx":
            if job.doc_type == "cavaliere":
                buffer, filename = build_cavalieri_docx(menu)
            else:
                buffer, filename = build_menu_docx(menu)
            content_file = ContentFile(buffer.getvalue())
        else:
            bundle, filename = build_menu_bundle(menu, doc_type=job.doc_type, include_cavalieri=job.include_cavalieri)
            content_file = ContentFile(bundle.getvalue())

        job.result_file.save(filename, content_file, save=False)
        job.status = MenuDocumentJob.STATUS_SUCCESS
        job.progress = 100
        job.completed_at = timezone.now()
        job.save(update_fields=["status", "progress", "result_file", "completed_at", "updated_at"])
        logger.info("Documento menu generato", extra={"job_id": job_id, "menu_id": menu.id})
        return f"Job {job_id} completato"
    except Exception as exc:  # pragma: no cover - la propagazione viene verificata nei test
        job.status = MenuDocumentJob.STATUS_FAILED
        job.error_message = str(exc)
        job.progress = 100
        job.completed_at = timezone.now()
        job.save(update_fields=["status", "error_message", "progress", "completed_at", "updated_at"])
        logger.exception("Job di generazione documenti fallito", extra={"job_id": job_id})
        raise


@shared_task
def cleanup_expired_documents_task():
    """Rimuove i file generati scaduti per evitare accumulo su disco."""

    retention_days = getattr(settings, "MENU_DOCUMENT_MAX_AGE_DAYS", 30)
    cutoff = timezone.now() - timezone.timedelta(days=retention_days)
    expired_jobs = MenuDocumentJob.objects.filter(
        expires_at__lt=timezone.now()
    ) | MenuDocumentJob.objects.filter(completed_at__lt=cutoff)

    removed = 0
    for job in expired_jobs:
        if job.result_file:
            try:
                default_storage.delete(job.result_file.name)
            except Exception:
                logger.warning("Impossibile cancellare file documento scaduto", exc_info=True)
        job.delete()
        removed += 1

    logger.info("Pulizia documenti completata", extra={"removed": removed})
    return removed
