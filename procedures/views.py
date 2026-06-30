from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Procedure
from .forms import ProcedureForm
from accounts.models import User
from core.decorators import role_required
from core.utils import themed_render

@login_required
def procedure_list_view(request):
    """
    Displays a list of procedures.
    - Superadmins see all procedures.
    - Owners see all procedures for their company.
    - Other users see only procedures relevant to their role/sector.
    """
    user = request.user

    if user.role == 'superadmin':
        procedure_list = Procedure.objects.all()
    elif user.role == 'owner':
        procedure_list = Procedure.objects.filter(company=user.company) if user.company else Procedure.objects.none()
    else:
        # For other roles, filter by sector and ensure they also belong to the user's company
        if user.company:
            procedure_list = Procedure.objects.filter(
                sectors__role_key=user.role,
                company=user.company
            ).distinct()
        else:
            procedure_list = Procedure.objects.none()

    procedure_list = procedure_list.select_related('uploaded_by', 'company').prefetch_related('sectors')

    context = {
        'procedures': procedure_list,
        'page_title': "Elenco Procedure"
    }
    return themed_render(request, 'procedures/procedure_list.html', context)


@login_required
@role_required(['superadmin', 'owner'])
def procedure_upload_view(request):
    """
    Handles the upload of a new procedure.
    """
    if request.method == 'POST':
        form = ProcedureForm(request.POST, request.FILES)
        if form.is_valid():
            # The form's save method is now simplified.
            # We handle the logic here in the view.
            procedure = form.save(commit=False)
            procedure.uploaded_by = request.user
            if request.user.company:
                procedure.company = request.user.company
            procedure.save()
            form.save_m2m()  # Save the many-to-many data for sectors
            messages.success(request, "Procedura caricata con successo.")
            return redirect('procedures:procedure_list')
    else:
        form = ProcedureForm()

    context = {
        'form': form,
        'page_title': "Carica Nuova Procedura"
    }
    return themed_render(request, 'procedures/procedure_form.html', context)


@login_required
@role_required(['superadmin', 'owner'])
def procedure_update_view(request, pk):
    """
    Handles the update of an existing procedure.
    """
    user = request.user
    queryset = Procedure.objects.all()
    # Owners can only update procedures in their own company.
    if user.role == 'owner' and user.company:
        queryset = queryset.filter(company=user.company)

    procedure = get_object_or_404(queryset, pk=pk)

    if request.method == 'POST':
        form = ProcedureForm(request.POST, request.FILES, instance=procedure)
        if form.is_valid():
            updated_procedure = form.save(commit=False)
            # Increment version only if the file has changed
            if 'file' in form.changed_data:
                updated_procedure.version += 1
            updated_procedure.save()
            form.save_m2m()
            messages.success(request, f"Procedura '{procedure.title}' aggiornata con successo.")
            return redirect('procedures:procedure_list')
    else:
        form = ProcedureForm(instance=procedure)

    context = {
        'form': form,
        'page_title': f"Modifica Procedura: {procedure.title}"
    }
    return themed_render(request, 'procedures/procedure_form.html', context)


@login_required
@role_required(['superadmin', 'owner'])
def procedure_delete_view(request, pk):
    """
    Handles the deletion of a procedure.
    """
    user = request.user
    queryset = Procedure.objects.all()
    # Owners can only delete procedures in their own company.
    if user.role == 'owner' and user.company:
        queryset = queryset.filter(company=user.company)

    procedure = get_object_or_404(queryset, pk=pk)

    if request.method == 'POST':
        procedure_title = procedure.title
        procedure.delete()
        messages.success(request, f"Procedura '{procedure_title}' eliminata con successo.")
        return redirect('procedures:procedure_list')

    context = {
        'procedure': procedure,
        'page_title': f"Conferma Eliminazione: {procedure.title}"
    }
    return themed_render(request, 'procedures/procedure_confirm_delete.html', context)


@login_required
def procedure_viewer_view(request, pk):
    """
    Displays a single procedure PDF file in-app.
    Checks if the user has permission to view it based on role and company.
    """
    user = request.user
    queryset = Procedure.objects.all()

    # Filter based on company for non-superadmins
    if user.role != 'superadmin':
        if user.company:
            queryset = queryset.filter(company=user.company)
        else:
            # If a non-superadmin user has no company, they can't see any procedures.
            queryset = Procedure.objects.none()

    # Further filter by sector for non-owner/superadmin roles
    if user.role not in ['superadmin', 'owner']:
        queryset = queryset.filter(sectors__role_key=user.role)

    procedure = get_object_or_404(queryset.distinct(), pk=pk)

    context = {
        'procedure': procedure,
        'page_title': f"Visualizza: {procedure.title}"
    }
    return themed_render(request, 'procedures/procedure_viewer.html', context)
