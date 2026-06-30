from django.urls import path
from . import views

app_name = 'inventory'

urlpatterns = [
    path('', views.InventoryItemListView.as_view(), name='list'),
    path('new/', views.InventoryItemCreateView.as_view(), name='create'),
    path('<int:pk>/', views.InventoryItemDetailView.as_view(), name='detail'),
    path('<int:item_pk>/adjust/', views.StockAdjustmentCreateView.as_view(), name='adjust_stock'),
]
