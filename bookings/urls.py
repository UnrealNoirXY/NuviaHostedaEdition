from django.urls import path
from . import views

app_name = 'bookings'

urlpatterns = [
    path('checkin/<str:token>/', views.checkin_wizard, name='checkin_wizard'),
    path('api/checkin/ocr/', views.checkin_ocr_view, name='checkin_ocr'),
    path('api/checkin/logs/', views.checkin_client_log_view, name='checkin_logs'),

    # URL per la conformità GDPR
    path('export/<str:token>/', views.data_export_view, name='data_export'),
    path('erasure/<str:token>/', views.data_erasure_view, name='data_erasure'),

    # URL per il nuovo cruscotto grafico
    path('dashboard/', views.booking_dashboard_view, name='dashboard'),

    # URL per la pagina di successo e download PDF
    path('checkin/complete/<int:booking_id>/', views.checkin_complete_view, name='checkin_complete'),
    path('download-pdf/<int:booking_id>/', views.download_pdf_view, name='download_pdf'),
    path('artifact-status/<int:booking_id>/', views.artifact_status_view, name='artifact_status'),

    # URL per il download sicuro dei documenti
    path('documents/<int:pk>/', views.serve_doc, name='serve_document'),
]