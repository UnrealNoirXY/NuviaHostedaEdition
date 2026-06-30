app_name = 'menu_generator_api'

from rest_framework.routers import DefaultRouter
from .views import (
    AllergeneViewSet,
    IngredienteViewSet,
    BaseFoodItemViewSet,
    PiattoViewSet,
    LayoutTemplateViewSet,
    CavaliereTemplateViewSet,
    MenuViewSet,
    PermissionSummaryViewSet,
)

router = DefaultRouter()
router.register(r'allergeni', AllergeneViewSet, basename='allergene')
router.register(r'ingredienti', IngredienteViewSet, basename='ingrediente')
router.register(r'alimenti-base', BaseFoodItemViewSet, basename='alimento-base')
router.register(r'piatti', PiattoViewSet, basename='piatto')
router.register(r'layouts', LayoutTemplateViewSet, basename='layout')
router.register(r'cavalieri', CavaliereTemplateViewSet, basename='cavaliere')
router.register(r'menu', MenuViewSet, basename='menu')
router.register(r'permissions', PermissionSummaryViewSet, basename='permissions')

from .views import ExecutiveDashboardViewSet, PublicPiattoDetailView
from django.urls import path

router.register(r'executive-dashboard', ExecutiveDashboardViewSet, basename='executive-dashboard')

urlpatterns = [
    path('public/piatto/<uuid:piatto_uuid>/', PublicPiattoDetailView.as_view(), name='public-piatto-detail'),
] + router.urls
