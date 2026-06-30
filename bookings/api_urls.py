from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import api

app_name = 'bookings_api'

# Il router gestisce automaticamente gli URL per il ViewSet
router = DefaultRouter()
router.register(r'bookings', api.BookingViewSet, basename='booking')

urlpatterns = [
    # L'URL per la dashboard rimane separato
    path('dashboard/', api.dashboard_api_view, name='dashboard'),
    # URL per le opzioni dei form (società, resort)
    path('form-options/', api.form_options_api_view, name='form_options'),

    # URL per il polling dello stato del documento
    path('documents/<int:doc_id>/status/<str:token>/', api.document_status_api_view, name='document_status'),

    # URL per il reinvio dell'OTP
    path('otp/resend/<str:token>/', api.resend_otp_api_view, name='resend_otp'),

    # Il router aggiunge gli URL per le operazioni CRUD (es. /api/bookings/bookings/)
    path('', include(router.urls)),
]