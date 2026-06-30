from django.urls import path
from .views import (
    MenuCreationStudioView,
    GenerateMenuDocumentView,
)

app_name = 'menu_generator'

urlpatterns = [
    path('', MenuCreationStudioView.as_view(), name='studio'),
    path('menu/<int:menu_id>/documenti/', GenerateMenuDocumentView.as_view(), name='generate_documents'),
]
