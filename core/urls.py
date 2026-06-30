from django.urls import path
from . import views
from tickets import views as tickets_views

app_name = 'core'

urlpatterns = [
    path('', views.management_dashboard, name='management_dashboard'),
    path('nuvia-mail/', views.nuvia_mail_landing_view, name='nuvia_mail'),
    path('api/nuvia-mail/providers/status/', views.nuvia_mail_provider_status_api, name='nuvia_mail_provider_status_api'),
    path('api/nuvia-mail/providers/presets/', views.nuvia_mail_provider_presets_api, name='nuvia_mail_provider_presets_api'),
    path('api/nuvia-mail/accounts/test-connection/', views.nuvia_mail_test_connection_api, name='nuvia_mail_test_connection_api'),
    path('api/nuvia-mail/accounts/', views.nuvia_mail_save_account_api, name='nuvia_mail_save_account_api'),
    path('api/nuvia-mail/accounts/connect/', views.nuvia_mail_account_connect_api, name='nuvia_mail_account_connect_api'),
    path('api/nuvia-mail/accounts/oauth/callback/', views.nuvia_mail_oauth_callback_api, name='nuvia_mail_oauth_callback_api'),
    path('api/nuvia-mail/compliance/preview/', views.nuvia_mail_compliance_preview_api, name='nuvia_mail_compliance_preview_api'),
    path('api/nuvia-mail/queue/process/', views.nuvia_mail_process_queue_api, name='nuvia_mail_process_queue_api'),
    path('api/nuvia-mail/queue/', views.nuvia_mail_queue_list_api, name='nuvia_mail_queue_list_api'),
    path('api/nuvia-mail/queue/analytics/', views.nuvia_mail_queue_analytics_api, name='nuvia_mail_queue_analytics_api'),
    path('api/nuvia-mail/queue/<int:item_id>/approve/', views.nuvia_mail_approve_queue_item_api, name='nuvia_mail_approve_queue_item_api'),
    path('api/nuvia-mail/queue/<int:item_id>/reject/', views.nuvia_mail_reject_queue_item_api, name='nuvia_mail_reject_queue_item_api'),
    path('api/nuvia-mail/sync/run/', views.nuvia_mail_sync_run_api, name='nuvia_mail_sync_run_api'),
    path('api/nuvia-mail/folders/', views.nuvia_mail_folders_api, name='nuvia_mail_folders_api'),
    path('api/nuvia-mail/threads/', views.nuvia_mail_threads_api, name='nuvia_mail_threads_api'),
    path('api/nuvia-mail/threads/<int:thread_id>/', views.nuvia_mail_thread_detail_api, name='nuvia_mail_thread_detail_api'),
    path('users/', views.user_list_view, name='user_list'),
    path('users/new/', views.user_create_view, name='user_create'),
    path('users/<int:pk>/edit/', views.user_update_view, name='user_update'),
    path('users/<int:pk>/delete/', views.user_delete_view, name='user_delete'),

    # Resort Management
    path('resorts/', views.resort_list_view, name='resort_list'),
    path('resorts/new/', views.resort_create_view, name='resort_create'),
    path('resorts/<int:pk>/edit/', views.resort_update_view, name='resort_update'),
    path('resorts/<int:pk>/delete/', views.resort_delete_view, name='resort_delete'),

    # Room Management (New Multi-Page Flow)
    path('rooms/', views.room_management_landing_view, name='room_management_landing'),
    path('rooms/select-company/', views.select_company_view, name='select_company'),
    path('rooms/select-resort/', views.select_resort_view, name='select_resort_owner'),
    path('rooms/select-resort/<int:company_id>/', views.select_resort_view, name='select_resort'),
    path('rooms/list/<int:resort_id>/', views.resort_room_list_view, name='resort_room_list'),
    path('rooms/create/bulk/<int:resort_id>/', views.room_bulk_create_form_view, name='room_bulk_create'),
    path('rooms/<int:pk>/edit/', views.room_update_view, name='room_update'),
    path('rooms/<int:pk>/delete/', views.room_delete_view, name='room_delete'),

    # API for bulk creation
    path('api/rooms/bulk-create/', views.room_bulk_create_api_view, name='api_room_bulk_create'),
    path('api/guides/assets/', views.GuideAssetApiView.as_view(), name='guide_assets_api'),

    # Reporting
    path('reporting/', views.reporting_view, name='reporting'),
    path('reporting/export/csv/', views.export_tickets_csv, name='export_tickets_csv'),
    path('admin-logs/', views.admin_logs_view, name='admin_logs'),
    path('admin-logs/export/csv/', views.export_admin_logs_csv, name='export_admin_logs_csv'),
    path('admin-logs/export/excel/', views.export_admin_logs_excel, name='export_admin_logs_excel'),
    path('admin-logs/export/pdf/', views.export_admin_logs_pdf, name='export_admin_logs_pdf'),

    # Ticket Management (for Superadmin)
    path('tickets/', tickets_views.ticket_list_view, name='ticket_list'),
    path('tickets/<int:pk>/edit/', tickets_views.ticket_update_view, name='ticket_update'),
    path('tickets/<int:pk>/delete/', tickets_views.ticket_delete_view, name='ticket_delete'),

    # Director's Cockpit
    path('cruscotto-direzione/', views.director_cockpit_view, name='director_cockpit'),

    # Head Maintainer Dashboard
    path('dashboard/head-maintainer/', views.dashboard_head_maintainer, name='dashboard_head_maintainer'),

    # Demo Views
    path('demo/tickets/', views.demo_tickets_view, name='demo_tickets'),
    path('demo/reviews/', views.demo_reviews_view, name='demo_reviews'),
    path('demo/dashboard/', views.demo_dashboard_view, name='demo_dashboard'),
]
