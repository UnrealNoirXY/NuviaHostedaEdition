import React, { useEffect, useState } from 'react';
import apiClient from '../apiClient';
import NoirWidgetWrapper from '../components/NoirWidgetWrapper';

const priorityLabels = {
    urgent: 'Urgente',
    high: 'Alta',
    medium: 'Media',
    low: 'Bassa',
};

const formatDueDate = (isoString) => {
    if (!isoString) {
        return 'Senza scadenza';
    }
    const date = new Date(isoString);
    return date.toLocaleString('it-IT', {
        hour: '2-digit',
        minute: '2-digit',
        day: '2-digit',
        month: '2-digit',
    });
};

const UrgentTicketsWidget = () => {
    const [tickets, setTickets] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        let isMounted = true;
        apiClient.get('/api/desk/widget-data/urgent-tickets/')
            .then((response) => {
                if (!isMounted) return;
                setTickets(response.data);
                setLoading(false);
            })
            .catch((err) => {
                console.error('Errore nel recupero dei ticket urgenti', err);
                if (!isMounted) return;
                setError('Impossibile caricare i ticket urgenti.');
                setLoading(false);
            });
        return () => {
            isMounted = false;
        };
    }, []);

    const handleNavigate = (ticketId) => {
        window.location.href = `/tickets/${ticketId}/`;
    };

    if (loading) {
        return <div className="widget-loading">Caricamento...</div>;
    }

    if (error) {
        return <div className="widget-error">{error}</div>;
    }

    const actions = [
        { label: 'Nuovo Ticket', icon: 'fa-plus', variant: 'btn-primary', onClick: () => window.location.assign('/maintenance/ticket/nuovo/') },
        { label: 'Vai alla Lista', icon: 'fa-list', onClick: () => window.location.assign('/tickets/') }
    ];

    if (tickets.length === 0) {
        return (
            <NoirWidgetWrapper actions={actions}>
                <div className="widget-empty">Nessun ticket urgente o in scadenza.</div>
            </NoirWidgetWrapper>
        );
    }

    return (
        <NoirWidgetWrapper actions={actions}>
            <ul className="widget-list" role="list">
                {tickets.map((ticket) => (
                    <li key={ticket.id} className={`widget-list-item ${ticket.is_overdue ? 'is-overdue' : ''}`}>
                    <button
                        type="button"
                        className="widget-list-button"
                        onClick={() => handleNavigate(ticket.id)}
                    >
                        <div className="widget-list-content">
                            <p className="widget-list-title">#{ticket.id} · {ticket.title}</p>
                            <p className="widget-list-subtitle">
                                Scadenza: {formatDueDate(ticket.due_date)} · Apertura: {ticket.age_hours}h fa
                            </p>
                        </div>
                        <span className={`priority-chip priority-${ticket.priority}`}>
                            {priorityLabels[ticket.priority] || ticket.priority}
                        </span>
                    </button>
                </li>
                ))}
            </ul>
        </NoirWidgetWrapper>
    );
};

export default UrgentTicketsWidget;
