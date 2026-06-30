from celery import shared_task

from .models import PayslipPreviewJob


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_jitter=True, retry_kwargs={"max_retries": 3})
def process_payslip_preview_job(self, job_id):
    preview_job = PayslipPreviewJob.objects.filter(pk=job_id).first()
    if not preview_job:
        return {"status": "missing", "job_id": job_id}
    preview_job._run_processing()
    return {"status": preview_job.status, "job_id": str(preview_job.pk)}
