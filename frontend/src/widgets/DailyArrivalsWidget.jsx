import React, { useEffect, useState } from 'react';
import apiClient from '../apiClient';
import NoirWidgetWrapper from '../components/NoirWidgetWrapper';

const DailyArrivalsWidget = () => {
    const [arrivals, setArrivals] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        apiClient.get('/api/desk/widget-data/daily-arrivals/')
            .then(res => {
                setArrivals(res.data);
                setLoading(false);
            })
            .catch(err => {
                setError('Errore caricamento arrivi.');
                setLoading(false);
            });
    }, []);

    const actions = [
        { label: 'Invia Benvenuto', icon: 'fa-envelope', variant: 'btn-primary' },
        { label: 'Fast Check-in', icon: 'fa-bolt' }
    ];

    if (loading) return <div className="widget-loading">Caricamento...</div>;

    const handleDragStart = (e, booking) => {
        const context = {
            type: 'guest',
            id: booking.id,
            name: booking.guest_name,
            room: booking.room_details,
            source: 'DailyArrivalsWidget'
        };
        e.dataTransfer.setData('application/nuvia-context', JSON.stringify(context));
        e.dataTransfer.effectAllowed = 'copy';
    };

    return (
        <NoirWidgetWrapper actions={actions}>
            <div className="daily-arrivals-list">
                {arrivals.length === 0 ? (
                    <div className="widget-empty">Nessun arrivo previsto per oggi.</div>
                ) : (
                    arrivals.map(booking => (
                        <div
                            key={booking.id}
                            className="arrival-item glass"
                            draggable
                            onDragStart={(e) => handleDragStart(e, booking)}
                            style={{ cursor: 'grab' }}
                        >
                            <div className="arrival-info">
                                <span className="guest-name">{booking.guest_name}</span>
                                <span className="room-details">{booking.room_details}</span>
                            </div>
                            <div className="arrival-status">
                                <span className={`status-pill ${booking.status}`}>{booking.status}</span>
                                <span className="arrival-time">{booking.check_in_time}</span>
                            </div>
                        </div>
                    ))
                )}
            </div>
        </NoirWidgetWrapper>
    );
};

export default DailyArrivalsWidget;
