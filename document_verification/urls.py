from django.urls import path
from .views import DocumentVerificationView

app_name = 'document_verification'

urlpatterns = [
    path('verify/', DocumentVerificationView.as_view(), name='verify_document'),
]
