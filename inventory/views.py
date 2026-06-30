from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.utils.decorators import method_decorator
from django.views.generic import ListView, DetailView, CreateView
from django.urls import reverse_lazy
from .models import InventoryItem, StockRecord
from accounts.models import User
from core.decorators import inventory_access_required

class InventoryQuerysetMixin:
    """
    Mixin to filter inventory items based on the user's role.
    """
    model = InventoryItem

    def get_queryset(self):
        user = self.request.user
        queryset = super().get_queryset().select_related('resort', 'resort__company')

        if user.is_superuser or user.role == User.ADMINISTRATIVE:
            return queryset
        if user.role in [User.OWNER, User.CAPO_ECONOMO]:
            return queryset.filter(resort__company=user.company) if user.company else queryset.none()
        if user.role in [User.DIRECTOR, User.ECONOMO, User.MAINTAINER]:
            return queryset.filter(resort=user.resort) if user.resort else queryset.none()

        return queryset.none() # If no role matches and no resort/company is assigned, show nothing.

@method_decorator(login_required, name='dispatch')
@method_decorator(inventory_access_required, name='dispatch')
class InventoryItemListView(InventoryQuerysetMixin, ListView):
    template_name = 'inventory/inventoryitem_list.html'
    context_object_name = 'items'
    paginate_by = 25

@method_decorator(login_required, name='dispatch')
@method_decorator(inventory_access_required, name='dispatch')
class InventoryItemDetailView(InventoryQuerysetMixin, DetailView):
    template_name = 'inventory/inventoryitem_detail.html'
    context_object_name = 'item'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['stock_records'] = StockRecord.objects.filter(item=self.object).order_by('-timestamp')
        return context

from .forms import StockAdjustmentForm, InventoryItemForm
from django.db import transaction

@method_decorator(login_required, name='dispatch')
@method_decorator(inventory_access_required, name='dispatch')
class InventoryItemCreateView(CreateView):
    model = InventoryItem
    form_class = InventoryItemForm
    template_name = 'inventory/inventoryitem_form.html'
    success_url = reverse_lazy('inventory:list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        with transaction.atomic():
            # Save the item first
            self.object = form.save()
            # If there's an initial stock, create a stock record for it
            if self.object.current_stock > 0:
                StockRecord.objects.create(
                    item=self.object,
                    change=self.object.current_stock,
                    reason='initial',
                    notes='Giacenza iniziale inserita alla creazione dell\'articolo.'
                )
        return super().form_valid(form)

@method_decorator(login_required, name='dispatch')
@method_decorator(inventory_access_required, name='dispatch')
class StockAdjustmentCreateView(CreateView):
    model = StockRecord
    form_class = StockAdjustmentForm
    template_name = 'inventory/stockadjustment_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['item'] = get_object_or_404(InventoryItem, pk=self.kwargs['item_pk'])
        return context

    def form_valid(self, form):
        with transaction.atomic():
            item = get_object_or_404(InventoryItem, pk=self.kwargs['item_pk'])
            stock_record = form.save(commit=False)
            stock_record.item = item
            stock_record.save()

            # Update the inventory item's stock
            item.current_stock += stock_record.change
            item.save()
        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse_lazy('inventory:detail', kwargs={'pk': self.kwargs['item_pk']})
