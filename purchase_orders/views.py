from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.decorators import method_decorator
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from .models import PurchaseOrder, Budget, Supplier, PurchaseCategory
from .forms import PurchaseOrderFilterForm, PurchaseOrderItemFormSet, PurchaseOrderForm
from accounts.models import User
from core.decorators import purchase_order_access_required, role_required

class PurchaseOrderQuerysetMixin:
    """
    Mixin to filter purchase orders based on the user's role and permissions.
    This ensures users can only see the orders they are allowed to see.
    """
    model = PurchaseOrder

    def get_queryset(self):
        user = self.request.user
        queryset = super().get_queryset()

        # Eager load related objects to improve performance
        if hasattr(queryset, 'select_related'):
            queryset = queryset.select_related('resort', 'supplier', 'created_by')

        # Apply role-based filtering
        if user.role in [User.SUPERADMIN, User.ADMINISTRATIVE]:
            return queryset

        if user.role == User.OWNER:
            if user.company:
                return queryset.filter(resort__company=user.company)
            return queryset.none()

        if user.role == User.DIRECTOR:
            if user.resort:
                return queryset.filter(resort=user.resort)
            return queryset.none()

        if user.role == User.HEAD_MAINTAINER:
            if user.company:
                try:
                    maintenance_category = PurchaseCategory.objects.get(name__iexact="Manutenzione")
                    return queryset.filter(resort__company=user.company, category=maintenance_category)
                except PurchaseCategory.DoesNotExist:
                    return queryset.none()
            return queryset.none()

        return queryset.filter(created_by=user)

@method_decorator(purchase_order_access_required, name='dispatch')
class PurchaseOrderListView(LoginRequiredMixin, PurchaseOrderQuerysetMixin, ListView):
    """
    Displays a list of purchase orders with filtering capabilities.
    """
    template_name = 'purchase_orders/purchaseorder_list.html'
    context_object_name = 'purchase_orders'
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset()
        self.filter_form = PurchaseOrderFilterForm(self.request.GET, user=self.request.user)

        if self.filter_form.is_valid():
            supplier = self.filter_form.cleaned_data.get('supplier')
            if supplier:
                queryset = queryset.filter(supplier=supplier)

            resort = self.filter_form.cleaned_data.get('resort')
            if resort:
                queryset = queryset.filter(resort=resort)

            start_date = self.filter_form.cleaned_data.get('start_date')
            if start_date:
                queryset = queryset.filter(created_at__gte=start_date)

            end_date = self.filter_form.cleaned_data.get('end_date')
            if end_date:
                queryset = queryset.filter(created_at__lte=end_date)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_form'] = self.filter_form
        return context

@method_decorator(purchase_order_access_required, name='dispatch')
class PurchaseOrderDetailView(LoginRequiredMixin, PurchaseOrderQuerysetMixin, DetailView):
    """
    Displays details of a single purchase order.
    """
    template_name = 'purchase_orders/purchaseorder_detail.html'
    context_object_name = 'order'

@method_decorator(purchase_order_access_required, name='dispatch')
class PurchaseOrderCreateView(LoginRequiredMixin, CreateView):
    """
    Handles the creation of a new purchase order.
    """
    model = PurchaseOrder
    form_class = PurchaseOrderForm
    template_name = 'purchase_orders/purchaseorder_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_success_url(self):
        return reverse_lazy('purchase_orders:update', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)

@method_decorator(purchase_order_access_required, name='dispatch')
class PurchaseOrderUpdateView(LoginRequiredMixin, PurchaseOrderQuerysetMixin, UpdateView):
    """
    Handles updating an existing purchase order and its items via a formset.
    """
    model = PurchaseOrder
    form_class = PurchaseOrderForm
    template_name = 'purchase_orders/purchaseorder_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_success_url(self):
        return reverse_lazy('purchase_orders:detail', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['item_formset'] = PurchaseOrderItemFormSet(self.request.POST, instance=self.object)
        else:
            context['item_formset'] = PurchaseOrderItemFormSet(instance=self.object)
        return context

    def form_valid(self, form):
        user = self.request.user
        # Head Maintainer Approval Logic
        if user.role == User.HEAD_MAINTAINER and 'status' in form.changed_data and form.cleaned_data['status'] == 'approved':
            # A Head Maintainer can only approve orders in the 'Maintenance' category.
            is_maintenance = self.object.category and self.object.category.name.lower() == 'manutenzione'
            if not is_maintenance:
                form.add_error('status', "Non hai il permesso di approvare ordini al di fuori della categoria Manutenzione.")
                return self.form_invalid(form)

        context = self.get_context_data()
        item_formset = context['item_formset']
        if item_formset.is_valid():
            self.object = form.save()
            item_formset.instance = self.object
            item_formset.save()
            return super().form_valid(form)
        else:
            return self.render_to_response(self.get_context_data(form=form))

@method_decorator(purchase_order_access_required, name='dispatch')
class PurchaseOrderDeleteView(LoginRequiredMixin, PurchaseOrderQuerysetMixin, DeleteView):
    """
    Handles deleting a purchase order.
    """
    template_name = 'purchase_orders/purchaseorder_confirm_delete.html'
    success_url = reverse_lazy('purchase_orders:list')
    context_object_name = 'order'

# --- Export Views ---

from django.http import HttpResponse
from django.template.loader import render_to_string
from weasyprint import HTML
import openpyxl

@method_decorator(purchase_order_access_required, name='dispatch')
class PurchaseOrderPDFView(LoginRequiredMixin, PurchaseOrderQuerysetMixin, DetailView):
    """
    Generates a PDF representation of a single Purchase Order.
    """
    model = PurchaseOrder
    template_name = 'purchase_orders/purchaseorder_pdf.html' # To be created

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        html_string = render_to_string(self.template_name, {'order': self.object})

        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="ordine_{self.object.pk}.pdf"'

        HTML(string=html_string, base_url=request.build_absolute_uri()).write_pdf(response)
        return response

@method_decorator(purchase_order_access_required, name='dispatch')
class PurchaseOrderExcelView(LoginRequiredMixin, PurchaseOrderQuerysetMixin, ListView):
    """
    Generates an Excel file listing purchase orders based on current filters.
    """
    def get(self, request, *args, **kwargs):
        queryset = self.get_queryset()

        workbook = openpyxl.Workbook()
        worksheet = workbook.active
        worksheet.title = "Buoni d'Ordine"

        headers = ["ID Ordine", "Resort", "Fornitore", "Stato", "Data Creazione", "Creato Da", "Importo Totale"]
        worksheet.append(headers)

        for order in queryset:
            row = [
                order.id,
                order.resort.name,
                order.supplier.name,
                order.get_status_display(),
                order.created_at.strftime("%Y-%m-%d"),
                order.created_by.username if order.created_by else "",
                order.total_amount
            ]
            worksheet.append(row)

        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename="buoni_d_ordine.xlsx"'

        workbook.save(response)
        return response

# --- Budget Views ---

BUDGET_MANAGEMENT_ROLES = [User.DIRECTOR, User.OWNER, User.SUPERADMIN]

@method_decorator(login_required, name='dispatch')
@method_decorator(role_required(BUDGET_MANAGEMENT_ROLES), name='dispatch')
class BudgetListView(ListView):
    # This view will be more complex, maybe a TemplateView with a form.
    # For now, a simple ListView to lay the groundwork.
    model = Budget
    template_name = 'purchase_orders/budget_list.html' # To be created
    context_object_name = 'budgets'

    def get_queryset(self):
        user = self.request.user
        queryset = super().get_queryset().select_related('resort')

        if user.role == User.SUPERADMIN:
            return queryset
        if user.role == User.OWNER:
            return queryset.filter(resort__company=user.company) if user.company else queryset.none()
        if user.role == User.DIRECTOR:
            return queryset.filter(resort=user.resort) if user.resort else queryset.none()
        return queryset.none() # Should not be reached due to BudgetAccessMixin

@method_decorator(login_required, name='dispatch')
@method_decorator(role_required(BUDGET_MANAGEMENT_ROLES), name='dispatch')
class BudgetCreateView(CreateView):
    model = Budget
    template_name = 'purchase_orders/budget_form.html' # To be created
    fields = ['resort', 'year', 'month', 'category', 'amount']
    success_url = reverse_lazy('purchase_orders:budget_list')

    # TODO: Add logic to restrict resort choices based on user role.

@method_decorator(login_required, name='dispatch')
@method_decorator(role_required(BUDGET_MANAGEMENT_ROLES), name='dispatch')
class BudgetUpdateView(UpdateView):
    model = Budget
    template_name = 'purchase_orders/budget_form.html' # To be created
    fields = ['category', 'amount']
    success_url = reverse_lazy('purchase_orders:budget_list')

# --- Supplier Views ---

# --- Supplier Views ---

SUPPLIER_MANAGEMENT_ROLES = [User.ADMINISTRATIVE, User.DIRECTOR, User.OWNER, User.SUPERADMIN, User.CAPO_ECONOMO]

@method_decorator(login_required, name='dispatch')
@method_decorator(role_required(SUPPLIER_MANAGEMENT_ROLES), name='dispatch')
class SupplierListView(ListView):
    model = Supplier
    template_name = 'purchase_orders/supplier_list.html'
    context_object_name = 'suppliers'
    paginate_by = 20

    def get_queryset(self):
        user = self.request.user
        queryset = super().get_queryset()
        if user.is_superuser or user.role == User.ADMINISTRATIVE:
            return queryset
        if user.company:
            return queryset.filter(company=user.company)
        return queryset.none()

@method_decorator(login_required, name='dispatch')
@method_decorator(role_required(SUPPLIER_MANAGEMENT_ROLES), name='dispatch')
class SupplierCreateView(CreateView):
    model = Supplier
    template_name = 'purchase_orders/supplier_form.html'
    fields = ['name', 'contact_person', 'email', 'phone_number', 'address']
    success_url = reverse_lazy('purchase_orders:supplier_list')

    def form_valid(self, form):
        if not self.request.user.is_superuser and self.request.user.company:
            form.instance.company = self.request.user.company
        return super().form_valid(form)

@method_decorator(login_required, name='dispatch')
@method_decorator(role_required(SUPPLIER_MANAGEMENT_ROLES), name='dispatch')
class SupplierUpdateView(UpdateView):
    model = Supplier
    template_name = 'purchase_orders/supplier_form.html'
    fields = ['name', 'contact_person', 'email', 'phone_number', 'address']
    success_url = reverse_lazy('purchase_orders:supplier_list')

@method_decorator(login_required, name='dispatch')
@method_decorator(role_required(SUPPLIER_MANAGEMENT_ROLES), name='dispatch')
class SupplierDeleteView(DeleteView):
    model = Supplier
    template_name = 'purchase_orders/supplier_confirm_delete.html'
    success_url = reverse_lazy('purchase_orders:supplier_list')
    context_object_name = 'supplier'
