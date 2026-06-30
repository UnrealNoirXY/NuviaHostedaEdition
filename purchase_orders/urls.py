from django.urls import path
from . import views

app_name = 'purchase_orders'

urlpatterns = [
    # Purchase Order URLs
    path('', views.PurchaseOrderListView.as_view(), name='list'),
    path('new/', views.PurchaseOrderCreateView.as_view(), name='create'),
    path('<int:pk>/', views.PurchaseOrderDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', views.PurchaseOrderUpdateView.as_view(), name='update'),
    path('<int:pk>/delete/', views.PurchaseOrderDeleteView.as_view(), name='delete'),

    # Budget URLs
    path('budget/', views.BudgetListView.as_view(), name='budget_list'),
    path('budget/new/', views.BudgetCreateView.as_view(), name='budget_create'),
    path('budget/<int:pk>/edit/', views.BudgetUpdateView.as_view(), name='budget_update'),

    # Export URLs
    path('export/excel/', views.PurchaseOrderExcelView.as_view(), name='export_excel'),
    path('<int:pk>/export/pdf/', views.PurchaseOrderPDFView.as_view(), name='export_pdf'),

    # Supplier URLs
    path('fornitori/', views.SupplierListView.as_view(), name='supplier_list'),
    path('fornitori/new/', views.SupplierCreateView.as_view(), name='supplier_create'),
    path('fornitori/<int:pk>/edit/', views.SupplierUpdateView.as_view(), name='supplier_update'),
    path('fornitori/<int:pk>/delete/', views.SupplierDeleteView.as_view(), name='supplier_delete'),
]
