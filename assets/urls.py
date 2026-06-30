from django.urls import path
from . import views

app_name = 'assets'

urlpatterns = [
    # Asset URLs
    path('', views.AssetListView.as_view(), name='asset-list'),
    path('<int:pk>/', views.AssetDetailView.as_view(), name='asset-detail'),
    path('nuovo/', views.AssetCreateView.as_view(), name='asset-create'),
    path('<int:pk>/modifica/', views.AssetUpdateView.as_view(), name='asset-update'),
    path('<int:pk>/elimina/', views.AssetDeleteView.as_view(), name='asset-delete'),

    # Category URLs
    path('categorie/', views.AssetCategoryListView.as_view(), name='category-list'),
    path('categorie/nuova/', views.AssetCategoryCreateView.as_view(), name='category-create'),
    path('categorie/<int:pk>/modifica/', views.AssetCategoryUpdateView.as_view(), name='category-update'),
    path('categorie/<int:pk>/elimina/', views.AssetCategoryDeleteView.as_view(), name='category-delete'),
]
