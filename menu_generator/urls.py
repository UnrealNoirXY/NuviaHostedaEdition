from django.urls import path
from django.conf import settings
from core.views import decommissioned_module_view
from .views import (
    MenuCreationStudioView,
    GenerateMenuDocumentView,
)

app_name = 'menu_generator'

if settings.ENABLE_MENU_GENERATOR:
    urlpatterns = [
        path('', MenuCreationStudioView.as_view(), name='studio'),
        path('menu/<int:menu_id>/documenti/', GenerateMenuDocumentView.as_view(), name='generate_documents'),
    ]
else:
    urlpatterns = [
        path('', decommissioned_module_view, {'module': 'menu'}, name='studio'),
        path('menu/<int:menu_id>/documenti/', decommissioned_module_view, {'module': 'menu'}, name='generate_documents'),
    ]
