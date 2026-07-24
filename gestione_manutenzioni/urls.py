from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path, include, re_path
from core import views as core_views
from core import os_views as core_os_views
from core.api_views import MobileShellContextView
from tickets import views as tickets_views
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic.base import TemplateView
from core.vite_views import serve_vite_asset

urlpatterns = [
    re_path(r'^vite/(?P<asset_path>.+)$', serve_vite_asset, name='vite_asset'),
    re_path(r'^static/vite/(?P<asset_path>.+)$', serve_vite_asset, name='static_vite_asset'),
    path('robots.txt', TemplateView.as_view(template_name="robots.txt", content_type="text/plain")),
    path('maintenance-notice/', core_views.maintenance_page_view, name='maintenance_page'),
    path('admin/', admin.site.urls),
    path('', core_views.landing_page_view, name='landing_page'),
    path('hub/', core_views.home, name='home'),
    path('hub/preview/', core_os_views.os_hub_preview, name='os_hub_preview'),
    path('login/', core_views.login_view, name='login'),
    path('force-password-change/', core_views.force_password_change_view, name='force_password_change'),
    path('password-change-otp/', core_views.password_change_otp_view, name='password_change_otp'),
    path('privacy-resend/', core_views.resend_privacy_confirmation_view, name='privacy_resend'),
    path('logout/', core_views.logout_view, name='logout'),
    path('verify-2fa/', core_views.verify_2fa_view, name='verify_2fa'),
    path('privacy-policy/', core_views.privacy_policy_view, name='privacy_policy'),
    path('privacy-confirm/<str:token>/', core_views.privacy_consent_confirm_view, name='privacy_confirm'),

    # Password Reset URLs
    path('password-reset/',
         auth_views.PasswordResetView.as_view(
             template_name='core/password_reset_form.html',
             email_template_name='core/password_reset_email.txt',
             html_email_template_name='core/password_reset_email.html'
         ),
         name='password_reset'),
    path('password-reset/done/',
         auth_views.PasswordResetDoneView.as_view(template_name='core/password_reset_done.html'),
         name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/',
         auth_views.PasswordResetConfirmView.as_view(template_name='core/password_reset_confirm.html'),
         name='password_reset_confirm'),
    path('password-reset-complete/',
         auth_views.PasswordResetCompleteView.as_view(template_name='core/password_reset_complete.html'),
         name='password_reset_complete'),

    # Profile
    path('profilo/', core_views.profile_view, name='profile'),

    # Search
    path('search/', core_views.search_results_view, name='search_results'),

    # Notifications
    path('notifications/', include('notifications.urls')),

    # Tool Entrypoints & URLs
    path('maintenance/', include([
        path('', core_views.maintenance_tool_redirect_view, name='maintenance_tool_home'),
        path('dashboard/superadmin/', core_views.dashboard_superadmin, name='dashboard_superadmin'),
        path('dashboard/ticket/', core_views.ticket_dashboard, name='ticket_dashboard'),
        path('dashboard/housekeeping/', core_views.dashboard_housekeeping, name='dashboard_housekeeping'),
        path('dashboard/maintainer/', core_views.dashboard_maintainer, name='dashboard_maintainer'),
        path('dashboard/owner/', core_views.dashboard_owner, name='dashboard_owner'),
        path('ticket/nuovo/', tickets_views.ticket_create, name='ticket_create'),
        path('ticket/<int:ticket_id>/', tickets_views.ticket_detail, name='ticket_detail'),
        path('ticket/<int:pk>/reopen/', tickets_views.reopen_ticket_view, name='reopen_ticket'),
        path('ajax/load-rooms/', tickets_views.ajax_load_rooms, name='ajax_load_rooms'),
        path('ajax/load-maintainers/', tickets_views.ajax_load_maintainers, name='ajax_load_maintainers'),
        path('alerts/', tickets_views.proactive_alert_list_view, name='proactive_alert_list'),
        path('alerts/<int:pk>/address/', tickets_views.mark_alert_addressed, name='mark_alert_addressed'),
        path('management/', include('core.urls')),
    ])),

    path('clients/', include('clients.urls')),
    path('reviews/', include('reviews.urls')),
    path('impersonate/', include('impersonate.urls')),
    path('amministrazione/', include('documents.urls')),
    path('supporto-it/', include('it_support.urls')),
    path('assets/', include('assets.urls')),
    path('svago/', include('svago.urls')),
    path('comunicazioni/', include('communications.urls')),
    path('ordini/', include('purchase_orders.urls')),
    path('inventario/', include('inventory.urls')),
    path('economato/', include('economato.urls')),
    path('procedure/', include('procedures.urls')),
    path('competitors/', include('competitors.urls')),
    path('hr/', include(('hr_portal.urls', 'hr_portal'), namespace='hr_portal')),
    path('desk/', include('desk.urls')),
    path('bookings/', include('bookings.urls')),
    path('finanza/', include('financials.urls')),
    path('menu-generator/', include('menu_generator.urls')),

    path('cards/', include(('profile_cards.urls', 'profile_cards'), namespace='profile_cards')),

    # API URLs
    path('api/document-verification/', include('document_verification.urls', namespace='document_verification_api')),
    path('api/reviews/', include('reviews.api_urls')),
    path('api/desk/', include('desk.api_urls', namespace='desk_api')),
    path('api/bookings/', include('bookings.api_urls', namespace='bookings_api')),
    path('api/notifications/', include('notifications.api_urls', namespace='notifications_api')),
    path('api/maintenance/', include(('tickets.api_urls', 'tickets'), namespace='maintenance_api')),
    path('api/hr/', include('hr_portal.api_urls', namespace='hr_portal')),
    path('api/mobile-shell/context/', MobileShellContextView.as_view(), name='mobile_shell_context'),
    path('api/menu-generator/', include('menu_generator.api_urls', namespace='menu_generator_api')),
]

# Media file in sviluppo
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
