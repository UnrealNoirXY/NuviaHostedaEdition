from django.urls import path
from . import views

app_name = 'procedures'

urlpatterns = [
    path('', views.procedure_list_view, name='procedure_list'),
    path('upload/', views.procedure_upload_view, name='procedure_upload'),
    path('<int:pk>/update/', views.procedure_update_view, name='procedure_update'),
    path('<int:pk>/delete/', views.procedure_delete_view, name='procedure_delete'),
    path('<int:pk>/view/', views.procedure_viewer_view, name='procedure_viewer'),
]
