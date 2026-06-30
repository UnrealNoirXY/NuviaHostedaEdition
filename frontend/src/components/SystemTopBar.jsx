import React, { useState, useEffect } from 'react';
import apiClient from '../apiClient';

const SystemTopBar = ({ userName, role }) => {
    const [time, setTime] = useState(new Date());

    useEffect(() => {
        const timer = setInterval(() => setTime(new Date()), 10000);
        return () => clearInterval(timer);
    }, []);

    const [telemetry, setTelemetry] = useState({ occ: '78%', tkt: 12, rev: '€4.2k' });

    useEffect(() => {
        const fetchTelemetry = () => {
            apiClient.get('/api/desk/widget-data/director-kpis/')
                .then(res => {
                    if (res.data) {
                        setTelemetry({
                            occ: `${res.data.occupancy_rate}%`,
                            tkt: res.data.upcoming_arrivals, // Placeholder logic
                            rev: '€' + (res.data.rooms_occupied * 120 / 1000).toFixed(1) + 'k' // Simulated rev
                        });
                    }
                });
        };
        fetchTelemetry();
        const interval = setInterval(fetchTelemetry, 30000);
        return () => clearInterval(interval);
    }, []);

    return (
        <div className="nuvia-system-topbar glass">
            <div className="topbar-left">
                <div className="system-logo">
                    <img src="/static/img/logo.png" alt="Nuvia" />
                    <span>Nuvia OS</span>
                </div>
            </div>
            <div className="topbar-center">
                <div className="system-telemetry-hud">
                    <div className="hud-item" title="Occupancy">
                        <i className="fas fa-bed"></i>
                        <span className="neon-blue">{telemetry.occ}</span>
                    </div>
                    <div className="hud-item" title="Active Tickets">
                        <i className="fas fa-ticket-alt"></i>
                        <span className="neon-blue">{telemetry.tkt}</span>
                    </div>
                    <div className="hud-item" title="Daily Revenue">
                        <i className="fas fa-euro-sign"></i>
                        <span className="neon-blue">{telemetry.rev}</span>
                    </div>
                </div>
                <div className="system-clock">
                    {time.toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit', weekday: 'short', day: '2-digit', month: 'short' })}
                </div>
            </div>
            <div className="topbar-right">
                <div className="system-status-pills">
                    <div className="status-pill-item">
                        <i className="fas fa-wifi"></i>
                    </div>
                    <div className="status-pill-item">
                        <i className="fas fa-microchip"></i>
                        <span>{role}</span>
                    </div>
                </div>
                <div className="user-profile-lite">
                    <span>{userName}</span>
                    <div className="avatar-mini glass">
                        <i className="fas fa-user"></i>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default SystemTopBar;
