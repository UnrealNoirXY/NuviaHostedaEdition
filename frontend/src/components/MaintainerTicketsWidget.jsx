import React, { useState, useEffect } from 'react';
import apiClient from '../apiClient';

const MaintainerTicketsWidget = () => {
    const [tickets, setTickets] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        apiClient.get('/api/desk/widget-data/maintainer-tickets/')
            .then(response => {
                setTickets(response.data);
                setLoading(false);
            })
            .catch(err => {
                console.error("Error fetching tickets:", err);
                setError("Impossibile caricare i ticket.");
                setLoading(false);
            });
    }, []);

    if (loading) return <div className="widget-loading">Caricamento...</div>;
    if (error) return <div className="widget-error">{error}</div>;
    if (tickets.length === 0) {
        return <div className="widget-empty">Nessun ticket assegnato.</div>;
    }

    const handleRowClick = (ticketId) => {
        window.location.href = `/tickets/${ticketId}/`;
    };

    return (
        <div className="widget-table-container">
            <table className="widget-table">
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Titolo</th>
                        <th>Stato</th>
                        <th>Priorità</th>
                    </tr>
                </thead>
                <tbody>
                    {tickets.map(ticket => (
                        <tr key={ticket.id} onClick={() => handleRowClick(ticket.id)}>
                            <td>#{ticket.id}</td>
                            <td>{ticket.title}</td>
                            <td>
                                <span className={`status-badge status-${ticket.status}`}>{ticket.status}</span>
                            </td>
                            <td>{ticket.priority}</td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
};

export default MaintainerTicketsWidget;
