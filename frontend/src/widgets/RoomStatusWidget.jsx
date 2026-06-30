import React, { useEffect, useState } from 'react';
import apiClient from '../apiClient';
import NoirWidgetWrapper from '../components/NoirWidgetWrapper';

const RoomStatusWidget = () => {
    const [rooms, setRooms] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        apiClient.get('/api/desk/widget-data/room-status/')
            .then(res => {
                setRooms(res.data);
                setLoading(false);
            });
    }, []);

    const actions = [
        { label: 'Segnala Guasto', icon: 'fa-triangle-exclamation' },
        { label: 'Tutte Pulite', icon: 'fa-broom' }
    ];

    if (loading) return <div className="widget-loading">Caricamento...</div>;

    return (
        <NoirWidgetWrapper actions={actions}>
            <div className="room-status-grid">
                {rooms.map(room => (
                    <div key={room.id} className={`room-card glass status-${room.status}`}>
                        <span className="room-name">{room.name}</span>
                        <div className="status-dot"></div>
                    </div>
                ))}
            </div>
        </NoirWidgetWrapper>
    );
};

export default RoomStatusWidget;
