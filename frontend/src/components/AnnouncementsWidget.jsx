import React, { useState, useEffect } from 'react';
import apiClient from '../apiClient';

const AnnouncementsWidget = () => {
    const [announcements, setAnnouncements] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        apiClient.get('/api/desk/widget-data/announcements/')
            .then(response => {
                setAnnouncements(response.data);
                setLoading(false);
            })
            .catch(err => {
                console.error("Error fetching announcements:", err);
                setError("Impossibile caricare gli annunci.");
                setLoading(false);
            });
    }, []);

    if (loading) {
        return <div className="widget-loading">Caricamento...</div>;
    }
    if (error) {
        return <div className="widget-error">{error}</div>;
    }
    if (announcements.length === 0) {
        return <div className="widget-empty">Nessun annuncio da visualizzare.</div>;
    }

    return (
        <div className="announcements-list">
            {announcements.map(ann => (
                <a key={ann.id} href={`/communications/announcements/${ann.id}/`} className="announcement-item">
                    <strong className="announcement-title">{ann.title}</strong>
                    <p className="announcement-content mb-0">{ann.content}</p>
                </a>
            ))}
        </div>
    );
};

export default AnnouncementsWidget;
