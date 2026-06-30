import React from 'react';
import AnnouncementsWidget from './AnnouncementsWidget';
import CalendarWidget from './CalendarWidget';
import MaintainerTicketsWidget from './MaintainerTicketsWidget';
import ChatWidget from './ChatWidget';
import NotificationCenterWidget from '../widgets/NotificationCenterWidget';
import RecentActivityWidget from '../widgets/RecentActivityWidget';
import RecentReviewsWidget from '../widgets/RecentReviewsWidget';
import PlaceholderWidget from '../widgets/PlaceholderWidget';
import TicketOverviewWidget from '../widgets/TicketOverviewWidget';
import UrgentTicketsWidget from '../widgets/UrgentTicketsWidget';
import CriticalStockWidget from '../widgets/CriticalStockWidget';
import MaintainerQuickAccessWidget from '../widgets/MaintainerQuickAccessWidget';
import DirectorKpisWidget from '../widgets/DirectorKpisWidget';
import RoomStatusWidget from '../widgets/RoomStatusWidget';
import DailyArrivalsWidget from '../widgets/DailyArrivalsWidget';
import SystemPulseWidget from '../widgets/SystemPulseWidget';

const WidgetRenderer = ({ widgetId }) => {
    switch (widgetId) {
        case 'announcements-widget':
            return <AnnouncementsWidget />;
        case 'calendar-widget':
            return <CalendarWidget />;
        case 'maintainer-tickets-widget':
            return <MaintainerTicketsWidget />;
        case 'recent-reviews-widget':
            return <RecentReviewsWidget />;
        case 'notification-center-widget':
            return <NotificationCenterWidget />;
        case 'recent-activity-widget':
            return <RecentActivityWidget />;
        case 'chat-widget':
            return <ChatWidget />;
        case 'ticket-overview-widget':
            return <TicketOverviewWidget />;
        case 'urgent-tickets-widget':
            return <UrgentTicketsWidget />;
        case 'critical-stock-widget':
            return <CriticalStockWidget />;
        case 'maintainer-quick-access-widget':
            return <MaintainerQuickAccessWidget />;
        case 'director-kpis-widget':
            return <DirectorKpisWidget />;
        case 'room-status-widget':
            return <RoomStatusWidget />;
        case 'daily-arrivals-widget':
            return <DailyArrivalsWidget />;
        case 'system-pulse-widget':
            return <SystemPulseWidget />;
        default:
            return <PlaceholderWidget widgetId={widgetId} />;
    }
};

export default WidgetRenderer;
