import React, { useState, useEffect, useRef } from 'react';
import { getNuviaCommands } from '../utils/nuviaCommands';
import './SpotlightSearch.css';

const SpotlightSearch = ({ isOpen, onClose, onLaunch, availableWidgets, availableApps = [] }) => {
    const [query, setQuery] = useState('');
    const [results, setResults] = useState([]);
    const inputRef = useRef(null);

    useEffect(() => {
        if (isOpen && inputRef.current) {
            inputRef.current.focus();
        }
    }, [isOpen]);

    useEffect(() => {
        if (!query) {
            setResults([]);
            return;
        }

        const filteredWidgets = availableWidgets.filter(w =>
            w.name.toLowerCase().includes(query.toLowerCase())
        ).map(w => ({ ...w, type: 'App / Widget' }));

        const filteredApps = availableApps.filter(a =>
            a.name.toLowerCase().includes(query.toLowerCase())
        ).map(a => ({ ...a, type: 'App / Widget' }));

        const aiCommands = getNuviaCommands(query).map(cmd => ({
            ...cmd,
            type: 'AI Command'
        }));

        let filtered = [...aiCommands, ...filteredApps, ...filteredWidgets];

        // Simulate searching other objects (tickets, guests) if no high-priority match
        if (query.length > 2 && filtered.length < 5) {
            filtered.push({ id: 'search-ticket-1', name: `Ticket #${query}`, icon: 'fa-ticket-alt', type: 'Database Result' });
            filtered.push({ id: 'search-guest-1', name: `Ospite: ${query}`, icon: 'fa-user', type: 'Database Result' });
        }

        setResults(filtered);
    }, [query, availableWidgets, availableApps]);

    if (!isOpen) return null;

    const handleAction = (res) => {
        if (res.action) {
            if (res.action.type === 'redirect') window.location.assign(res.action.url);
            if (res.action.type === 'launch') onLaunch(res.action.targetId);
            if (res.action.type === 'event') document.dispatchEvent(new CustomEvent(res.action.name));
        } else if (res.url) {
            window.location.assign(res.url);
        } else {
            onLaunch(res.id || res);
        }
        onClose();
    };

    return (
        <div className="spotlight-overlay" onClick={onClose}>
            <div className="spotlight-container glass" onClick={e => e.stopPropagation()}>
                <div className="spotlight-header">
                    <i className="fas fa-magnifying-glass spotlight-icon"></i>
                    <input
                        ref={inputRef}
                        type="text"
                        placeholder="Cerca funzioni o impartisci comandi (es: 'nuovo ticket')..."
                        value={query}
                        onChange={e => setQuery(e.target.value)}
                        onKeyDown={e => {
                            if (e.key === 'Escape') onClose();
                            if (e.key === 'Enter' && results.length > 0) handleAction(results[0]);
                        }}
                    />
                    <div className="spotlight-hint">ESC</div>
                </div>
                <div className="spotlight-results custom-scrollbar">
                    {results.length > 0 ? (
                        results.map((res, index) => (
                            <div
                                key={res.id + index}
                                className="spotlight-result-item"
                                onClick={() => handleAction(res)}
                            >
                                <div className="result-icon-bg glass">
                                    <i className={`fas ${res.icon}`}></i>
                                </div>
                                <div className="result-info">
                                    <span className="result-name">
                                        {res.type === 'AI Command' && <span className="command-tag">NUVIA AI</span>}
                                        {res.name}
                                    </span>
                                    <span className="result-type">{res.description || res.type}</span>
                                </div>
                            </div>
                        ))
                    ) : query ? (
                        <div className="spotlight-no-results">Nessun comando o app trovata per "{query}"</div>
                    ) : (
                        <div className="spotlight-welcome">
                            <i className="fas fa-bolt-lightning"></i>
                            <span>Benvenuto in Nuvia Spotlight. Digita per agire.</span>
                            <div className="spotlight-suggestions">
                                <span onClick={() => setQuery('miei ticket')}>"i miei ticket"</span>
                                <span onClick={() => setQuery('stato camere')}>"stato camere"</span>
                                <span onClick={() => setQuery('nuova manutenzione')}>"nuova manutenzione"</span>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default SpotlightSearch;
