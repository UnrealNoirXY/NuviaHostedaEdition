from django.urls import path
from . import views

app_name = 'competitors'

urlpatterns = [
    # Competitor CRUD URLs
    path('', views.CompetitorListView.as_view(), name='competitor-list'),
    path('new/', views.CompetitorCreateView.as_view(), name='competitor-create'),
    path('<int:pk>/edit/', views.CompetitorUpdateView.as_view(), name='competitor-update'),
    path('<int:pk>/delete/', views.CompetitorDeleteView.as_view(), name='competitor-delete'),

    # Scraping Link Management (Modal via HTMX)
    path('<int:pk>/manage-links/', views.manage_competitor_links_modal, name='manage-links-modal'),
    path('scraping-link/<int:pk>/delete/', views.delete_scraping_link, name='delete-scraping-link'),

    # Association Management URL
    path('associations/resort/<int:resort_pk>/', views.ManageCompetitorAssociationsView.as_view(), name='manage-associations'),
    path('associations/<int:pk>/delete/', views.remove_competitor_association, name='remove-association'),

    # Manual Scraping Panel
    path('scraping-panel/', views.competitor_scraping_panel_view, name='scraping-panel'),
]
