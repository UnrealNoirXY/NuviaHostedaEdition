import React from 'react';
import './AppLauncher.css';

const AppLauncher = ({ isOpen, onClose, availableWidgets, availableApps = [], onLaunch, pinnedApps, onPin }) => {
    const [searchTerm, setSearchTerm] = React.useState('');

    if (!isOpen) return null;

    const allItems = [...availableWidgets, ...availableApps];

    const filteredItems = allItems.filter(item =>
        item.name.toLowerCase().includes(searchTerm.toLowerCase())
    );

    // Group items by category if available, otherwise "General"
    const categorizedItems = filteredItems.reduce((acc, item) => {
        const cat = item.category || (item.url ? 'applicazioni' : 'widget');
        if (!acc[cat]) acc[cat] = [];
        acc[cat].push(item);
        return acc;
    }, {});

    const categoryOrder = ['management', 'operations', 'identity', 'applicazioni', 'widget'];

    return (
        <div className="nuvia-launcher-overlay" onClick={onClose}>
            <div className="nuvia-launcher-panel glass" onClick={e => e.stopPropagation()}>
                <div className="launcher-header">
                    <div className="search-box glass">
                        <i className="fas fa-magnifying-glass"></i>
                        <input
                            type="text"
                            placeholder="Cerca funzioni, app o strumenti..."
                            autoFocus
                            value={searchTerm}
                            onChange={(e) => setSearchTerm(e.target.value)}
                        />
                    </div>
                </div>

                <div className="launcher-grid-container custom-scrollbar">
                    {Object.keys(categorizedItems).length > 0 ? (
                        categoryOrder.map(cat => (
                            categorizedItems[cat] && categorizedItems[cat].length > 0 && (
                                <div key={cat} className="launcher-category">
                                    <div className="launcher-category-title">
                                        {cat.charAt(0).toUpperCase() + cat.slice(1)}
                                    </div>
                                    <div className="launcher-grid">
                                        {categorizedItems[cat].map(item => (
                                            <div
                                                key={item.id}
                                                className="launcher-item"
                                                onClick={() => {
                                                    onLaunch(item.id);
                                                    onClose();
                                                }}
                                            >
                                                <div className="launcher-icon-wrapper glass">
                                                    <i className={`fas ${item.icon}`}></i>
                                                    <button
                                                        className={`pin-shortcut ${pinnedApps.includes(item.id) ? 'is-pinned' : ''}`}
                                                        onClick={(e) => {
                                                            e.stopPropagation();
                                                            onPin(item.id);
                                                        }}
                                                        title="Aggiungi al Desktop"
                                                    >
                                                        <i className="fas fa-thumbtack"></i>
                                                    </button>
                                                </div>
                                                <span className="launcher-label">{item.name}</span>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )
                        ))
                    ) : (
                        <div className="launcher-no-results">
                            Nessun risultato trovato per "{searchTerm}".
                        </div>
                    )}
                </div>

                <div className="launcher-footer">
                    <div className="user-profile-section">
                        <img src={document.body.dataset.avatarUrl} alt="Avatar" className="user-avatar" />
                        <div className="user-info">
                            <span className="user-name">{document.body.dataset.userName}</span>
                            <span className="user-role">{document.body.dataset.userRole}</span>
                        </div>
                    </div>
                    <div className="launcher-footer-actions">
                         <button className="power-button" title="Impostazioni Profilo" onClick={() => window.location.assign('/profile/')}>
                            <i className="fas fa-user-gear"></i>
                        </button>
                        <button className="power-button" title="Spegni Sessione" onClick={() => window.location.assign('/logout/')}>
                            <i className="fas fa-power-off"></i>
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default AppLauncher;
