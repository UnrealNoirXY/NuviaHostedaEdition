from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Company
from .forms import CompanyForm
from core.utils import themed_render

@login_required
def company_list(request):
    if not request.user.is_superuser:
        messages.error(request, "Accesso negato.")
        return redirect('home')

    companies = Company.objects.all()
    return themed_render(request, 'clients/company_list.html', {'companies': companies})

@login_required
def company_create(request):
    if not request.user.is_superuser:
        messages.error(request, "Accesso negato.")
        return redirect('home')

    if request.method == 'POST':
        form = CompanyForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Società creata con successo.")
            return redirect('clients:company_list')
    else:
        form = CompanyForm()

    return themed_render(request, 'clients/company_form.html', {'form': form, 'title': 'Crea Nuova Società'})

@login_required
def company_update(request, pk):
    if not request.user.is_superuser:
        messages.error(request, "Accesso negato.")
        return redirect('home')

    company = get_object_or_404(Company, pk=pk)
    if request.method == 'POST':
        form = CompanyForm(request.POST, request.FILES, instance=company)
        if form.is_valid():
            form.save()
            messages.success(request, "Società aggiornata con successo.")
            return redirect('clients:company_list')
    else:
        form = CompanyForm(instance=company)

    return themed_render(request, 'clients/company_form.html', {'form': form, 'title': f'Modifica Società: {company.name}'})

@login_required
def company_delete(request, pk):
    if not request.user.is_superuser:
        messages.error(request, "Accesso negato.")
        return redirect('home')

    company = get_object_or_404(Company, pk=pk)
    if request.method == 'POST':
        company.delete()
        messages.success(request, "Società eliminata con successo.")
        return redirect('clients:company_list')

    return themed_render(request, 'clients/company_confirm_delete.html', {'company': company})
