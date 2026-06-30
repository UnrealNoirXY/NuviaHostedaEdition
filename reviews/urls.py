from django.urls import path, include
from . import views

app_name = 'reviews'

urlpatterns = [
    path('analysis-center/', views.analysis_center_view, name='analysis_center'),
    path('analysis-center/export/pdf/', views.export_analysis_pdf, name='export_analysis_pdf'),
    path('analysis-center/export/csv/', views.export_analysis_csv, name='export_analysis_csv'),
    path('dashboard/', views.review_dashboard_view, name='dashboard'),
    path('report-builder/', views.report_builder_view, name='report_builder'),
    path('all/', views.review_list_view, name='review_list'),
    path('review/<int:pk>/', views.review_detail_view, name='review_detail'),
    path('scraping-panel/', views.scraping_panel_view, name='scraping_panel'),
    path('resort/<int:resort_id>/manage-urls/', views.manage_scraping_urls, name='manage_scraping_urls'),
    path('scraping-url/<int:pk>/delete/', views.delete_scraping_url, name='delete_scraping_url'),

    # Scheduled Scraping URLs
    path('scheduled-scraping/', views.ScheduledScrapingListView.as_view(), name='scheduled_scraping_list'),
    path('scheduled-scraping/new/', views.ScheduledScrapingCreateView.as_view(), name='scheduled_scraping_create'),
    path('scheduled-scraping/<int:pk>/update/', views.ScheduledScrapingUpdateView.as_view(), name='scheduled_scraping_update'),
    path('scheduled-scraping/<int:pk>/delete/', views.ScheduledScrapingDeleteView.as_view(), name='scheduled_scraping_delete'),

    # Veratour Upload Wizard
    path('veratour/upload/', views.veratour_upload_wizard_view, name='veratour_upload'),
    path('veratour/task-status/<str:task_id>/', views.veratour_task_status_api, name='veratour_task_status'),
]
