import React, { useEffect, useMemo, useState } from 'react';
import apiClient from '../apiClient';

const STATUS_LABELS = {
    open: 'Aperti',
    in_progress: 'In lavorazione',
    resolved: 'Risolti',
    closed: 'Chiusi',
};

const TicketOverviewWidget = () => {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        let isMounted = true;
        apiClient.get('/api/desk/widget-data/ticket-overview/')
            .then((response) => {
                if (!isMounted) return;
                setData(response.data);
                setLoading(false);
            })
            .catch((err) => {
                console.error('Errore nel recupero del ticket overview', err);
                if (!isMounted) return;
                setError('Impossibile caricare la panoramica dei ticket.');
                setLoading(false);
            });
        return () => {
            isMounted = false;
        };
    }, []);

    const statusDistribution = useMemo(() => {
        if (!data) return [];
        const total = Object.values(data.status_counts || {}).reduce((sum, value) => sum + value, 0);
        if (!total) return [];
        return Object.entries(data.status_counts).map(([status, value]) => ({
            status,
            value,
            percentage: Math.round((value / total) * 100),
        }));
    }, [data]);

    const priorityList = useMemo(() => {
        if (!data) return [];
        return Object.entries(data.priority_counts || {})
            .sort(([, a], [, b]) => b - a)
            .map(([priority, value]) => ({ priority, value }));
    }, [data]);

    if (loading) {
        return <div className="widget-loading">Caricamento...</div>;
    }

    if (error) {
        return <div className="widget-error">{error}</div>;
    }

    if (!data) {
        return <div className="widget-empty">Nessun dato disponibile.</div>;
    }

    return (
        <div className="widget-ticket-overview">
            <div className="widget-metric-grid">
                <div className="widget-metric">
                    <p className="widget-metric-label">Ticket attivi</p>
                    <p className="widget-metric-value">{data.active_count}</p>
                    <p className="widget-metric-subtitle">{data.active_count === 1 ? 'Ticket aperto' : 'Ticket aperti o in lavorazione'}</p>
                </div>
                <div className="widget-metric">
                    <p className="widget-metric-label">Ticket in ritardo</p>
                    <p className="widget-metric-value text-danger">{data.overdue_count}</p>
                    <p className="widget-metric-subtitle">Scadenza superata</p>
                </div>
                <div className="widget-metric">
                    <p className="widget-metric-label">Risolti 7gg</p>
                    <p className="widget-metric-value text-success">{data.resolved_last_week}</p>
                    <p className="widget-metric-subtitle">Ultimi sette giorni</p>
                </div>
                <div className="widget-metric">
                    <p className="widget-metric-label">Tempo medio chiusura</p>
                    <p className="widget-metric-value">
                        {data.average_resolution_hours != null ? `${data.average_resolution_hours}h` : 'n/d'}
                    </p>
                    <p className="widget-metric-subtitle">Dalla creazione alla chiusura</p>
                </div>
            </div>

            <div className="widget-status-bars">
                {statusDistribution.length === 0 && (
                    <p className="widget-empty mb-0">Nessun ticket registrato nel periodo.</p>
                )}
                {statusDistribution.map(({ status, value, percentage }) => (
                    <div key={status} className="widget-status-row">
                        <span className="widget-status-label">{STATUS_LABELS[status] || status}</span>
                        <div className="widget-status-bar" aria-hidden="true">
                            <div
                                className={`widget-status-bar-fill status-${status}`}
                                style={{ width: `${percentage}%` }}
                            ></div>
                        </div>
                        <span className="widget-status-value">{value}</span>
                    </div>
                ))}
            </div>

            <div className="widget-priority-list">
                {priorityList.map(({ priority, value }) => (
                    <div key={priority} className="widget-priority-item">
                        <span className={`priority-chip priority-${priority}`}>{priority}</span>
                        <span className="widget-priority-value">{value}</span>
                    </div>
                ))}
            </div>
        </div>
    );
};

export default TicketOverviewWidget;
