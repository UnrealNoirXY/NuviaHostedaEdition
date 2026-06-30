import React, { useState, useEffect } from 'react';
import apiClient from '../apiClient';

const NotificationCenterWidget = () => {
    const [notifications, setNotifications] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const fetchNotifications = () => {
        setLoading(true);
        apiClient.get('/api/notifications/feed/', { params: { limit: 8 } })
            .then(response => {
                setNotifications(response.data?.results || []);
                setLoading(false);
            })
            .catch(err => {
                console.error("Error fetching notifications:", err);
                setError("Impossibile caricare le notifiche.");
                setLoading(false);
            });
    };

    useEffect(() => {
        fetchNotifications();
    }, []);

    const handleInvitationAction = (invitationId, status) => {
        // Optimistically remove the notification from the UI
        setNotifications(notifications.filter(n => n.metadata?.invitation_id !== invitationId));

        apiClient.post(`/api/desk/invitations/${invitationId}/update-status/`, { status })
            .then(response => {
                // Can optionally show a success message
                console.log(`Invitation ${invitationId} status updated to ${status}`);
                // Potentially refetch calendar events if the calendar is visible
            })
            .catch(err => {
                console.error("Error updating invitation status:", err);
                // If the API call fails, refetch notifications to revert the optimistic update
                fetchNotifications();
                // You could also show an error message to the user
            });
    };

    if (loading) return <div className="widget-loading">Caricamento...</div>;
    if (error) return <div className="widget-error">{error}</div>;
    if (notifications.length === 0) {
        return <div className="widget-empty">Nessuna nuova notifica.</div>;
    }

    const renderNotificationContent = (notification) => {
        if (notification.type === 'event_invitation') {
            return (
                <div className="notification-item-content">
                    <div className="notification-text">
                        <strong className="notification-title">{notification.title}</strong>
                        <p className="notification-body mb-0">{notification.content}</p>
                    </div>
                    <div className="notification-actions">
                        <button
                            className="btn btn-sm btn-success"
                            onClick={() => handleInvitationAction(notification.metadata?.invitation_id, 'accepted')}
                        >
                            Accetta
                        </button>
                        <button
                            className="btn btn-sm btn-danger"
                            onClick={() => handleInvitationAction(notification.metadata?.invitation_id, 'declined')}
                        >
                            Rifiuta
                        </button>
                    </div>
                </div>
            );
        }

        // Default rendering for announcements or other types
        return (
            <div className="notification-item-content">
                <div className="notification-text">
                    <strong className="notification-title">{notification.title}</strong>
                    <p className="notification-body mb-0">{notification.body || notification.content}</p>
                </div>
            </div>
        );
    };

    const getNotificationIcon = (type) => {
        switch(type) {
            case 'event_invitation': return 'fa-calendar-plus';
            case 'announcement': return 'fa-bullhorn';
            default: return 'fa-bell';
        }
    }

    return (
        <div className="notification-list">
            {notifications.map(notification => (
                <div key={notification.id} className="notification-item">
                    <div className="notification-icon">
                        <i className={`fas ${notification.icon || getNotificationIcon(notification.type)}`}></i>
                    </div>
                    {renderNotificationContent(notification)}
                </div>
            ))}
        </div>
    );
};

export default NotificationCenterWidget;
