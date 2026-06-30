from django.urls import path
from . import api

app_name = 'desk_api'

urlpatterns = [
    path('layout/', api.UserLayoutView.as_view(), name='user_layout'),
    path('widget-data/announcements/', api.AnnouncementsWidgetDataView.as_view(), name='widget_data_announcements'),
    path('widget-data/notification-center/', api.NotificationCenterDataView.as_view(), name='widget_data_notification_center'),
    path('widget-data/recent-activity/', api.RecentActivityDataView.as_view(), name='widget_data_recent_activity'),
    path('widget-data/calendar/', api.CalendarWidgetDataView.as_view(), name='widget_data_calendar'),
    path('widget-data/maintainer-tickets/', api.MaintainerTicketsWidgetDataView.as_view(), name='widget_data_maintainer_tickets'),
    path('widget-data/recent-reviews/', api.RecentReviewsWidgetDataView.as_view(), name='widget_data_recent_reviews'),
    path('widget-data/ticket-overview/', api.TicketOverviewWidgetDataView.as_view(), name='widget_data_ticket_overview'),
    path('widget-data/urgent-tickets/', api.UrgentTicketsWidgetDataView.as_view(), name='widget_data_urgent_tickets'),
    path('widget-data/maintainer-quick-access/', api.MaintainerQuickAccessWidgetDataView.as_view(), name='widget_data_maintainer_quick_access'),
    path('widget-data/critical-stock/', api.CriticalStockWidgetDataView.as_view(), name='widget_data_critical_stock'),
    path('widget-data/room-status/', api.RoomStatusWidgetDataView.as_view(), name='widget_data_room_status'),
    path('widget-data/daily-arrivals/', api.DailyArrivalsWidgetDataView.as_view(), name='widget_data_daily_arrivals'),
    path('widget-data/financial-performance/', api.FinancialPerformanceWidgetDataView.as_view(), name='widget_data_financial_performance'),
    path('widget-data/director-kpis/', api.DirectorKpisWidgetDataView.as_view(), name='widget_data_director_kpis'),
    path('smart-alerts/', api.SmartAlertsView.as_view(), name='smart_alerts'),
    path('search-invitees/', api.SearchInviteesView.as_view(), name='search_invitees'),
    path('events/', api.EventViewSet.as_view(), name='events'),
    path('invitations/<int:invitation_id>/update-status/', api.UpdateInvitationStatusView.as_view(), name='update_invitation_status'),
]
