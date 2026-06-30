import React, { useState, useEffect } from 'react';
import apiClient from '../apiClient';

const SystemPulseWidget = () => {
    const [telemetry, setTelemetry] = useState({
        occupancy: 0,
        tickets: 0,
        revenue: 0,
        efficiency: 0
    });

    useEffect(() => {
        const fetchData = () => {
            apiClient.get('/api/desk/widget-data/director-kpis/')
                .then(res => {
                    if (res.data) {
                        setTelemetry({
                            occupancy: res.data.occupancy_rate || 78,
                            tickets: res.data.upcoming_arrivals || 12,
                            revenue: 4.2, // Simulated
                            efficiency: 85 // Simulated
                        });
                    }
                });
        };
        fetchData();
        const interval = setInterval(fetchData, 30000);
        return () => clearInterval(interval);
    }, []);

    return (
        <div className="razer-pulse-widget">
            <div className="pulse-grid">
                <div className="pulse-item">
                    <div className="pulse-label">System Load</div>
                    <div className="pulse-value neon-green">Nominal</div>
                    <div className="pulse-neon-bar">
                        <div className="bar-fill green" style={{ width: '25%' }}></div>
                    </div>
                </div>
                <div className="pulse-item">
                    <div className="pulse-label">Efficiency</div>
                    <div className="pulse-value neon-blue">{telemetry.efficiency}%</div>
                    <div className="pulse-neon-bar">
                        <div className="bar-fill blue" style={{ width: `${telemetry.efficiency}%` }}></div>
                    </div>
                </div>
                <div className="pulse-item">
                    <div className="pulse-label">Occupancy</div>
                    <div className="pulse-value neon-purple">{telemetry.occupancy}%</div>
                    <div className="pulse-neon-bar">
                        <div className="bar-fill purple" style={{ width: `${telemetry.occupancy}%` }}></div>
                    </div>
                </div>
            </div>
            <div className="pulse-heartbeat">
                <div className="heartbeat-line"></div>
            </div>
        </div>
    );
};

export default SystemPulseWidget;
