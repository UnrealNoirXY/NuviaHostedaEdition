from django.urls import path

from . import views

app_name = 'financials'

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),
    path('snapshots/', views.snapshot_list_view, name='snapshot_list'),
    path('snapshots/new/', views.snapshot_create_view, name='snapshot_create'),
    path('snapshots/<int:pk>/edit/', views.snapshot_update_view, name='snapshot_update'),
    path('snapshots/<int:pk>/delete/', views.snapshot_delete_view, name='snapshot_delete'),
    path('periods/new/', views.period_create_view, name='period_create'),
    path('periods/<int:pk>/edit/', views.period_update_view, name='period_update'),
]
