from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from .models import Asset, AssetCategory
from .forms import AssetForm, AssetCategoryForm
from core.mixins import StaffRequiredMixin

# --- Asset Views ---

class AssetListView(StaffRequiredMixin, ListView):
    model = Asset
    template_name = 'assets/asset_list.html'
    context_object_name = 'assets'
    paginate_by = 20

class AssetDetailView(StaffRequiredMixin, DetailView):
    model = Asset
    template_name = 'assets/asset_detail.html'
    context_object_name = 'asset'

class AssetCreateView(StaffRequiredMixin, CreateView):
    model = Asset
    form_class = AssetForm
    template_name = 'assets/asset_form.html'
    success_url = reverse_lazy('assets:asset-list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Crea Nuovo Asset'
        return context

class AssetUpdateView(StaffRequiredMixin, UpdateView):
    model = Asset
    form_class = AssetForm
    template_name = 'assets/asset_form.html'
    success_url = reverse_lazy('assets:asset-list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Modifica Asset'
        return context

class AssetDeleteView(StaffRequiredMixin, DeleteView):
    model = Asset
    template_name = 'assets/asset_confirm_delete.html'
    success_url = reverse_lazy('assets:asset-list')

# --- AssetCategory Views ---

class AssetCategoryListView(StaffRequiredMixin, ListView):
    model = AssetCategory
    template_name = 'assets/asset_category_list.html'
    context_object_name = 'categories'

class AssetCategoryCreateView(StaffRequiredMixin, CreateView):
    model = AssetCategory
    form_class = AssetCategoryForm
    template_name = 'assets/asset_category_form.html'
    success_url = reverse_lazy('assets:category-list')

class AssetCategoryUpdateView(StaffRequiredMixin, UpdateView):
    model = AssetCategory
    form_class = AssetCategoryForm
    template_name = 'assets/asset_category_form.html'
    success_url = reverse_lazy('assets:category-list')

class AssetCategoryDeleteView(StaffRequiredMixin, DeleteView):
    model = AssetCategory
    template_name = 'assets/asset_category_confirm_delete.html'
    success_url = reverse_lazy('assets:category-list')
