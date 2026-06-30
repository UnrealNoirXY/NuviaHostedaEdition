from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from .models import Resort, ReviewSource
from .tasks import process_veratour_upload_task
from celery.result import AsyncResult
import os

@login_required
def veratour_upload_wizard_view(request):
    """
    Wizard view to handle Veratour Excel uploads.
    """
    # Permission check: Only certain roles or superusers can upload Veratour data
    allowed_roles = ['owner', 'director', 'corporate', 'superadmin']
    if not (request.user.is_superuser or request.user.role in allowed_roles):
        messages.error(request, "Non hai il permesso di caricare dati Veratour.")
        return redirect('reviews:dashboard')

    step = int(request.POST.get('step', 1)) if request.method == 'POST' else 1

    if request.method == 'POST':
        if step == 1:
            resort_id = request.POST.get('resort_id')
            if resort_id:
                resort = get_object_or_404(Resort, pk=resort_id)
                return render(request, 'reviews/veratour_wizard.html', {
                    'step': 2,
                    'resort_id': resort.id,
                    'resort_name': resort.name
                })

        elif step == 2:
            resort_id = request.POST.get('resort_id')
            max_capacity = request.POST.get('max_capacity')
            file_report = request.FILES.get('file_report')
            file_commenti = request.FILES.get('file_commenti')

            if resort_id and file_report and file_commenti:
                resort = get_object_or_404(Resort, pk=resort_id)

                # Save files temporarily for Celery
                path_report = default_storage.save(f'tmp/veratour/report_{resort_id}_{os.urandom(4).hex()}.xlsx', ContentFile(file_report.read()))
                path_commenti = default_storage.save(f'tmp/veratour/commenti_{resort_id}_{os.urandom(4).hex()}.xlsx', ContentFile(file_commenti.read()))

                full_path_report = default_storage.path(path_report)
                full_path_commenti = default_storage.path(path_commenti)

                # Trigger Celery Task
                task = process_veratour_upload_task.delay(resort_id, full_path_report, full_path_commenti, max_capacity)

                return render(request, 'reviews/veratour_wizard.html', {
                    'step': 3,
                    'task_id': task.id,
                    'resort_name': resort.name
                })

    # Default Step 1
    resorts = Resort.objects.all()
    if request.user.role == 'director' and request.user.resort:
        resorts = resorts.filter(pk=request.user.resort.pk)
    elif request.user.company:
        resorts = resorts.filter(company=request.user.company)

    return render(request, 'reviews/veratour_wizard.html', {
        'step': 1,
        'resorts': resorts
    })

@login_required
def veratour_task_status_api(request, task_id):
    """
    API to poll Celery task status.
    """
    task_result = AsyncResult(task_id)
    result_data = task_result.result if task_result.ready() else task_result.info

    return JsonResponse({
        'task_id': task_id,
        'state': task_result.state,
        'result': result_data
    })
