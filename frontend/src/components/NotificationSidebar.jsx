import React, { useState, useEffect } from 'react';
import apiClient from '../apiClient';

const NotificationSidebar = ({ isOpen, onClose, onAction }) => {
    const [events, setEvents] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (isOpen) {
            apiClient.get('/api/desk/widget-data/notification-center/')
                .then(res => {
                    setEvents(res.data);
                    setLoading(false);
                });
        }
    }, [isOpen]);

    return (
        <div className={`noir-notification-sidebar glass ${isOpen ? 'sidebar-open' : ''}`}>
            <div className="sidebar-header">
                <h3>Workflow</h3>
                <button className="btn-close-sidebar" onClick={onClose}>
                    <i className="fas fa-times"></i>
                </button>
            </div>
            <div className="sidebar-body">
                {loading ? (
                    <div className="sidebar-loading">Caricamento...</div>
                ) : events.length === 0 ? (
                    <div className="sidebar-empty">Nessun progresso recente.</div>
                ) : (
                    events.map((event, idx) => (
                        <div key={idx} className="sidebar-event-card glass">
                            <div className="event-meta">
                                <i className={`fas ${event.icon || 'fa-info-circle'} event-icon`}></i>
                                <span className="event-time">{new Date(event.date).toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit' })}</span>
                            </div>
                            <h4 className="event-title">{event.title}</h4>
                            <p className="event-desc">{event.content}</p>
                            {event.cta_url && (
                                <button
                                    className="btn btn-xs btn-outline-primary mt-2"
                                    onClick={() => onAction(event)}
                                >
                                    {event.cta_label || 'Gestisci'}
                                </button>
                            )}
                        </div>
                    ))
                )}
            </div>
        </div>
    );
};

export default NotificationSidebar;
