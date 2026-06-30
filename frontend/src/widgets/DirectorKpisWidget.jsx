import React, { useEffect, useState } from 'react';
import apiClient from '../apiClient';
import NoirWidgetWrapper from '../components/NoirWidgetWrapper';

const DirectorKpisWidget = () => {
    const [snapshot, setSnapshot] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        let isMounted = true;
        apiClient.get('/api/desk/widget-data/director-kpis/')
            .then((response) => {
                if (!isMounted) return;
                setSnapshot(response.data);
                setLoading(false);
            })
            .catch((err) => {
                console.error('Errore nel recupero dei KPI direzionali', err);
                if (!isMounted) return;
                setError('Impossibile caricare i KPI di direzione.');
                setLoading(false);
            });
        return () => {
            isMounted = false;
        };
    }, []);

    if (loading) {
        return <div className="widget-loading">Caricamento...</div>;
    }

    if (error) {
        return <div className="widget-error">{error}</div>;
    }

    if (!snapshot) {
        return <div className="widget-empty">Nessun dato disponibile.</div>;
    }

    const actions = [
        { label: 'Scarica Report', icon: 'fa-file-pdf', onClick: () => console.log('Downloading PDF...') },
        { label: 'Invia Notifica', icon: 'fa-paper-plane', onClick: () => console.log('Sending Notification...') }
    ];

    return (
        <NoirWidgetWrapper actions={actions}>
            <div className="widget-metric-grid">
                <div className="widget-metric">
                    <p className="widget-metric-label">Occupazione odierna</p>
                    <p className="widget-metric-value">{snapshot.occupancy_rate}%</p>
                    <p className="widget-metric-subtitle">{snapshot.rooms_occupied} camere occupate</p>
                </div>
                <div className="widget-metric">
                    <p className="widget-metric-label">Check-in previsti</p>
                    <p className="widget-metric-value">{snapshot.upcoming_arrivals}</p>
                    <p className="widget-metric-subtitle">Oggi</p>
                </div>
                <div className="widget-metric">
                    <p className="widget-metric-label">Check-in da verificare</p>
                    <p className="widget-metric-value">{snapshot.pending_checkins}</p>
                    <p className="widget-metric-subtitle">Azioni richieste</p>
                </div>
                <div className="widget-metric">
                    <p className="widget-metric-label">Permanenza media</p>
                    <p className="widget-metric-value">{snapshot.avg_stay_nights} notti</p>
                    <p className="widget-metric-subtitle">Ultime prenotazioni confermate</p>
                </div>
                <div className="widget-metric">
                    <p className="widget-metric-label">Punteggio recensioni</p>
                    <p className="widget-metric-value">{snapshot.avg_review_score ?? 'n/d'}</p>
                    <p className="widget-metric-subtitle">{snapshot.recent_reviews_count} recensioni 30gg</p>
                </div>
                <div className="widget-metric">
                    <p className="widget-metric-label">Ultima recensione</p>
                    <p className="widget-metric-value">
                        {snapshot.last_review_date ? new Date(snapshot.last_review_date).toLocaleDateString('it-IT') : 'n/d'}
                    </p>
                    <p className="widget-metric-subtitle">Aggiornamento reputazione</p>
                </div>
            </div>
        </NoirWidgetWrapper>
    );
};

export default DirectorKpisWidget;
