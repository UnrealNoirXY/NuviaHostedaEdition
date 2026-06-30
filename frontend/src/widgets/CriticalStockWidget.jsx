import React, { useEffect, useState } from 'react';
import apiClient from '../apiClient';

const CriticalStockWidget = () => {
    const [items, setItems] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        let isMounted = true;
        apiClient.get('/api/desk/widget-data/critical-stock/')
            .then((response) => {
                if (!isMounted) return;
                setItems(response.data);
                setLoading(false);
            })
            .catch((err) => {
                console.error('Errore nel recupero delle scorte critiche', err);
                if (!isMounted) return;
                setError('Impossibile caricare le scorte critiche.');
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

    if (items.length === 0) {
        return <div className="widget-empty">Nessun articolo è sotto la soglia critica.</div>;
    }

    return (
        <div className="widget-critical-stock">
            <div className="widget-critical-stock-header">
                <span>Articolo</span>
                <span>Giacenza</span>
                <span>Copertura</span>
            </div>
            <ul className="widget-critical-stock-list" role="list">
                {items.map((item) => (
                    <li key={item.id} className="widget-critical-stock-item">
                        <div>
                            <p className="widget-list-title">{item.name}</p>
                            <p className="widget-list-subtitle">{item.resort_name || 'Multi-sede'} · Consumo 30gg: {item.monthly_usage}</p>
                        </div>
                        <span className="stock-pill" aria-label={`Giacenza attuale ${item.current_stock}`}>{item.current_stock}</span>
                        <span className={`coverage-pill ${item.coverage_days != null && item.coverage_days <= 3 ? 'is-warning' : ''}`}>
                            {item.coverage_days != null ? `${item.coverage_days} giorni` : 'n/d'}
                        </span>
                    </li>
                ))}
            </ul>
        </div>
    );
};

export default CriticalStockWidget;
