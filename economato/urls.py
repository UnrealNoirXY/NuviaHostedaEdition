from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r'categories', views.EconomatoCategoryViewSet, basename='economato-categories')
router.register(r'cost-centers', views.EconomatoCostCenterViewSet, basename='economato-cost-centers')
router.register(r'items', views.EconomatoItemViewSet, basename='economato-items')
router.register(r'stock-levels', views.EconomatoStockLevelViewSet, basename='economato-stock-levels')
router.register(r'requests', views.EconomatoRequestViewSet, basename='economato-requests')

app_name = 'economato'

urlpatterns = [
    path('app/', views.EconomatoReactAppView.as_view(), name='app'),
    path('api/overview/', views.EconomatoOverviewAPIView.as_view(), name='overview'),
    path('api/requests/<int:request_id>/timeline/', views.EconomatoTimelineView.as_view(), name='timeline'),
    path('api/', include(router.urls)),
]
