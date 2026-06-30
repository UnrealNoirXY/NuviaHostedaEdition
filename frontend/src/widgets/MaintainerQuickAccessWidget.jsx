import React, { useEffect, useState } from 'react';
import apiClient from '../apiClient';

const MaintainerQuickAccessWidget = () => {
    const [snapshot, setSnapshot] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        let isMounted = true;
        apiClient.get('/api/desk/widget-data/maintainer-quick-access/')
            .then((response) => {
                if (!isMounted) return;
                setSnapshot(response.data);
                setLoading(false);
            })
            .catch((err) => {
                console.error('Errore nel recupero del riepilogo manutentori', err);
                if (!isMounted) return;
                setError('Impossibile caricare le scorciatoie manutenzione.');
                setLoading(false);
            });
        return () => {
            isMounted = false;
        };
    }, []);

    const handleAction = (action) => {
        if (action.href) {
            window.location.href = action.href;
        }
        if (action.target === 'open_assistant') {
            document.dispatchEvent(new CustomEvent('homeDesk.openAssistant'));
        }
    };

    if (loading) {
        return <div className="widget-loading">Caricamento...</div>;
    }

    if (error) {
        return <div className="widget-error">{error}</div>;
    }

    if (!snapshot) {
        return <div className="widget-empty">Nessun dato disponibile.</div>;
    }

    return (
        <div className="widget-quick-access">
            <div className="widget-metric-grid">
                <div className="widget-metric">
                    <p className="widget-metric-label">Assegnati a me</p>
                    <p className="widget-metric-value">{snapshot.assigned_to_me}</p>
                    <p className="widget-metric-subtitle">Ticket attivi</p>
                </div>
                <div className="widget-metric">
                    <p className="widget-metric-label">In scadenza oggi</p>
                    <p className={`widget-metric-value ${snapshot.due_today ? 'text-warning' : ''}`}>{snapshot.due_today}</p>
                    <p className="widget-metric-subtitle">Entro fine giornata</p>
                </div>
                <div className="widget-metric">
                    <p className="widget-metric-label">Da assegnare</p>
                    <p className="widget-metric-value">{snapshot.awaiting_assignment}</p>
                    <p className="widget-metric-subtitle">Ticket senza responsabile</p>
                </div>
            </div>

            {snapshot.next_due && (
                <div className="widget-next-ticket">
                    <div>
                        <p className="widget-list-title">Prossima scadenza · #{snapshot.next_due.id}</p>
                        <p className="widget-list-subtitle">{snapshot.next_due.title}</p>
                        <p className="widget-list-subtitle">Scade il {new Date(snapshot.next_due.due_date).toLocaleString('it-IT')}</p>
                    </div>
                    <button
                        type="button"
                        className="btn btn-sm btn-outline-light"
                        onClick={() => window.location.href = `/tickets/${snapshot.next_due.id}/`}
                    >
                        Apri ticket
                    </button>
                </div>
            )}

            <div className="widget-quick-actions" role="group" aria-label="Azioni rapide manutenzione">
                {snapshot.actions.map((action) => (
                    <button
                        key={action.label}
                        type="button"
                        className="btn btn-sm btn-primary"
                        onClick={() => handleAction(action)}
                    >
                        <i className={`fas ${action.icon} me-2`} aria-hidden="true"></i>
                        {action.label}
                    </button>
                ))}
            </div>
        </div>
    );
};

export default MaintainerQuickAccessWidget;
