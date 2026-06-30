from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from .models import Document
from .forms import DocumentForm, DocumentFilterForm
from accounts.models import User
from core.utils import themed_render
from django.db.models import Q

from core.decorators import role_required

@login_required
@role_required([User.ADMINISTRATIVE, User.SUPERADMIN, User.RISORSE_UMANE])
def document_list_view(request):
    user = request.user
    if user.is_superuser:
        documents = Document.objects.all()
    else: # Administrative or HR role
        if not user.company:
            messages.warning(request, "Non sei associato a nessuna società.")
            documents = Document.objects.none()
        else:
            documents = Document.objects.filter(user__company=user.company)

    documents = documents.select_related('user', 'user__resort', 'user__company')

    filter_form = DocumentFilterForm(request.GET)
    if filter_form.is_valid():
        name = filter_form.cleaned_data.get('name')
        if name:
            documents = documents.filter(
                Q(user__username__icontains=name) |
                Q(user__first_name__icontains=name) |
                Q(user__last_name__icontains=name)
            )

        resort = filter_form.cleaned_data.get('resort')
        if resort:
            documents = documents.filter(user__resort=resort)

        role = filter_form.cleaned_data.get('role')
        if role:
            documents = documents.filter(user__role=role)

    context = {
        'documents': documents,
        'filter_form': filter_form
    }
    if request.htmx:
        return render(request, 'documents/_document_table.html', context)

    return themed_render(request, 'documents/document_list.html', context)

@login_required
@role_required([User.ADMINISTRATIVE, User.SUPERADMIN, User.RISORSE_UMANE])
def document_upload_view(request):
    if request.method == 'POST':
        form = DocumentForm(request.POST, request.FILES, requesting_user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Documento caricato con successo.")
            return redirect('documents:document_list')
    else:
        form = DocumentForm(requesting_user=request.user)
    return themed_render(request, 'documents/document_upload.html', {'form': form})

@login_required
@role_required([User.ADMINISTRATIVE, User.SUPERADMIN, User.RISORSE_UMANE])
def document_delete_view(request, pk):
    user = request.user
    queryset = Document.objects.all()
    if not user.is_superuser:
        queryset = queryset.filter(user__company=user.company)

    document = get_object_or_404(queryset, pk=pk)
    if request.method == 'POST':
        document.delete()
        messages.success(request, "Documento eliminato con successo.")
        return redirect('documents:document_list')
    return themed_render(request, 'documents/document_confirm_delete.html', {'document': document})

@login_required
def document_view(request, pk):
    user = request.user
    queryset = Document.objects.all()

    # A regular user can only see their own documents
    if not (user.is_superuser or user.role in [User.ADMINISTRATIVE, User.RISORSE_UMANE]):
        queryset = queryset.filter(user=user)
    # An admin or HR can only see documents in their company
    elif not user.is_superuser:
        queryset = queryset.filter(user__company=user.company)

    document = get_object_or_404(queryset, pk=pk)

    document.read_by.add(request.user)
    return redirect(document.file.url)

@login_required
@role_required([User.ADMINISTRATIVE, User.SUPERADMIN, User.RISORSE_UMANE])
def document_report_view(request, pk):
    user = request.user
    queryset = Document.objects.prefetch_related('user', 'read_by')
    if not user.is_superuser:
        queryset = queryset.filter(user__company=user.company)

    document = get_object_or_404(queryset, pk=pk)

    context = {
        'document': document,
        'read_by_users': document.read_by.all(),
    }
    return themed_render(request, 'documents/document_report.html', context)
