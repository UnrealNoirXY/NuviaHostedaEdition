import React, { useState, useEffect } from 'react';
import apiClient from '../apiClient';
import moment from 'moment';

const RecentActivityWidget = () => {
    const [activities, setActivities] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        apiClient.get('/api/desk/widget-data/recent-activity/')
            .then(response => {
                setActivities(response.data);
                setLoading(false);
            })
            .catch(err => {
                console.error("Error fetching recent activity:", err);
                setError("Impossibile caricare l'attività recente.");
                setLoading(false);
            });
    }, []);

    const getIconForActivity = (type) => {
        switch (type) {
            case 'ticket_created':
                return 'fa-plus-circle text-success';
            case 'ticket_closed':
                return 'fa-check-circle text-primary';
            default:
                return 'fa-history text-secondary';
        }
    };

    if (loading) return <div className="widget-loading">Caricamento...</div>;
    if (error) return <div className="widget-error">{error}</div>;
    if (activities.length === 0) {
        return <div className="widget-empty">Nessuna attività recente da mostrare.</div>;
    }

    return (
        <div className="activity-list">
            {activities.map(activity => (
                <a key={activity.id} href={activity.url} className="activity-item">
                    <div className="activity-icon">
                        <i className={`fas ${getIconForActivity(activity.type)}`}></i>
                    </div>
                    <div className="activity-details">
                        <p className="activity-description mb-0">{activity.description}</p>
                        <small className="activity-date text-muted">
                            {moment(activity.date).fromNow()}
                        </small>
                    </div>
                </a>
            ))}
        </div>
    );
};

export default RecentActivityWidget;
