from django.urls import path
from . import views

app_name = 'documents'

urlpatterns = [
    path('', views.document_list_view, name='document_list'),
    path('upload/', views.document_upload_view, name='document_upload'),
    path('<int:pk>/delete/', views.document_delete_view, name='document_delete'),
    path('<int:pk>/view/', views.document_view, name='document_detail_view'),
    path('<int:pk>/report/', views.document_report_view, name='document_report'),
]
