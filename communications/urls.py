from django.urls import path
from . import views

app_name = 'communications'

urlpatterns = [
    # Announcements
    path('create/', views.create_announcement, name='create'),
    path('<int:pk>/', views.announcement_detail, name='detail'),
    path('<int:pk>/update/', views.announcement_update, name='update'),
    path('<int:pk>/delete/', views.announcement_delete, name='delete'),
    path('<int:pk>/report/', views.announcement_report, name='report'),

    # Scheduled Email Reports
    path('scheduled-reports/', views.ScheduledEmailReportListView.as_view(), name='scheduled_report_list'),
    path('scheduled-reports/create/', views.ScheduledEmailReportCreateView.as_view(), name='scheduled_report_create'),
    path('scheduled-reports/<int:pk>/update/', views.ScheduledEmailReportUpdateView.as_view(), name='scheduled_report_update'),
    path('scheduled-reports/<int:pk>/delete/', views.ScheduledEmailReportDeleteView.as_view(), name='scheduled_report_delete'),
    path('scheduled-reports/<int:pk>/send/', views.send_instant_report_view, name='scheduled_report_send_now'),
]
