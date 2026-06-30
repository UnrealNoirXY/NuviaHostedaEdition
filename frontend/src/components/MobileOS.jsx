import React, { useState, useEffect } from 'react';
import apiClient from '../apiClient';
import WidgetRenderer from './WidgetRenderer';
import { getNuviaCommands } from '../utils/nuviaCommands';
import './MobileOS.css';

const MobileOS = ({
    availableWidgets = [],
    availableApps = [],
    onLaunch,
}) => {
    const [currentTime, setCurrentTime] = useState(new Date());
    const [recentApps, setRecentApps] = useState(() => {
        const stored = localStorage.getItem('nuvia_mobile_recent_apps');
        return stored ? JSON.parse(stored) : [];
    });
    const [openApps, setOpenApps] = useState([]);
    const [activeAppId, setActiveAppId] = useState(null);
    const [activeTab, setActiveTab] = useState('home');
    const [searchQuery, setSearchQuery] = useState('');
    const [isSearchOpen, setIsSearchOpen] = useState(false);
    const [alerts, setAlerts] = useState([]);
    const [loadingAlerts, setLoadingAlerts] = useState(false);
    const [focusMode, setFocusMode] = useState(false);
    const [homeData, setHomeData] = useState({
        tickets: 0,
        arrivals: 0,
        occupancy: '78%',
        revenue: '€4.2k',
        recentActivity: [],
        loading: true
    });

    const tabs = ['home', 'status', 'launcher', 'profile', 'multitask'];

    useEffect(() => {
        const timer = setInterval(() => setCurrentTime(new Date()), 10000);
        return () => clearInterval(timer);
    }, []);

    useEffect(() => {
        const fetchHomeData = () => {
            setHomeData(prev => ({ ...prev, loading: true }));
            Promise.all([
                apiClient.get('/api/desk/widget-data/ticket-overview/').catch(() => ({ data: { active_count: 0 } })),
                apiClient.get('/api/desk/widget-data/daily-arrivals/').catch(() => ({ data: [] })),
                apiClient.get('/api/desk/widget-data/recent-activity/').catch(() => ({ data: [] })),
                apiClient.get('/api/desk/widget-data/director-kpis/').catch(() => ({ data: { occupancy_rate: 78 } }))
            ]).then(([ticketsRes, arrivalsRes, activityRes, kpiRes]) => {
                setHomeData({
                    tickets: ticketsRes.data.active_count || 0,
                    arrivals: arrivalsRes.data.length || 0,
                    occupancy: `${kpiRes.data.occupancy_rate}%`,
                    revenue: '€4.2k',
                    recentActivity: Array.isArray(activityRes.data) ? activityRes.data.slice(0, 3) : [],
                    loading: false
                });
            });
        };

        fetchHomeData();
        const interval = setInterval(fetchHomeData, 60000);
        return () => clearInterval(interval);
    }, []);

    const handleLaunchApp = (id) => {
        const app = [...availableApps, ...availableWidgets].find(i => i.id === id);
        if (app && (app.url || app.type === 'iframe')) {
            setOpenApps(prev => prev.includes(id) ? prev : [id, ...prev]);
            setActiveAppId(id);
            setRecentApps(prev => {
                const updated = [id, ...prev.filter(appId => appId !== id)].slice(0, 4);
                localStorage.setItem('nuvia_mobile_recent_apps', JSON.stringify(updated));
                return updated;
            });
        } else {
            onLaunch(id);
        }
        setIsSearchOpen(false);
    };

    const handleCommandAction = (cmd) => {
        if (cmd.action.type === 'redirect') window.location.assign(cmd.action.url);
        if (cmd.action.type === 'launch') handleLaunchApp(cmd.action.targetId);
        if (cmd.action.type === 'event') document.dispatchEvent(new CustomEvent(cmd.action.name));
        setIsSearchOpen(false);
    };

    // Swipe Logic
    const [touchStart, setTouchStart] = useState(null);
    const [touchEnd, setTouchEnd] = useState(null);
    const minSwipeDistance = 50;

    const onTouchStart = (e) => {
        setTouchEnd(null);
        setTouchStart(e.targetTouches[0].clientX);
    };

    const onTouchMove = (e) => setTouchEnd(e.targetTouches[0].clientX);

    const onTouchEnd = () => {
        if (!touchStart || !touchEnd) return;
        const distance = touchStart - touchEnd;
        const isLeftSwipe = distance > minSwipeDistance;
        const isRightSwipe = distance < -minSwipeDistance;

        if (isLeftSwipe || isRightSwipe) {
            const currentIndex = tabs.indexOf(activeTab);
            if (isLeftSwipe && currentIndex < tabs.length - 1) setActiveTab(tabs[currentIndex + 1]);
            if (isRightSwipe && currentIndex > 0) setActiveTab(tabs[currentIndex - 1]);
        }
    };

    const categorizedApps = {
        'Management': availableApps.filter(item => item.category === 'management'),
        'Operations': availableApps.filter(item => item.category === 'operations'),
        'Identity': availableApps.filter(item => item.category === 'identity'),
        'Widgets': availableWidgets.filter(item => item.id !== 'notification-center-widget')
    };

    const aiCommands = getNuviaCommands(searchQuery);

    return (
        <div
            className={`razer-mobile-shell nuvia-mobile-shell ${focusMode ? 'focus-active' : ''}`}
            onTouchStart={onTouchStart}
            onTouchMove={onTouchMove}
            onTouchEnd={onTouchEnd}
        >
            <div className="razer-ambient-glow"></div>

            <header className="razer-status-bar">
                <div className="status-left">
                    <span className="razer-clock">
                        {currentTime.toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit' })}
                    </span>
                </div>
                <div className="status-center">
                    <img src="/static/img/logo.png" alt="Nuvia" className="razer-logo-small" />
                </div>
                <div className="status-right">
                    <i className="fas fa-wifi"></i>
                    <i className="fas fa-battery-three-quarters"></i>
                </div>
            </header>

            <main className="razer-content">
                <div className={`razer-tab-viewport active-tab-${activeTab}`}>

                    {/* Home: Operational Pulse */}
                    <div className="razer-tab-page tab-home">
                        <div className="razer-greeting">
                            <span className="greeting-text">Buongiorno,</span>
                            <span className="greeting-name">{document.body.dataset.userName?.split(' ')[0] || 'Admin'}</span>
                        </div>
                        <div className="razer-section-title">Mission Control</div>

                        <div className="razer-search-trigger" onClick={() => setIsSearchOpen(true)}>
                            <i className="fas fa-magnifying-glass"></i>
                            <span>Cerca o chiedi a Nuvia...</span>
                            <div className="search-badge">AI</div>
                        </div>

                        <div className="pulse-summary-grid">
                            <div className="pulse-mini-card">
                                <span className="pulse-mini-label">Occupancy</span>
                                <span className="pulse-mini-value">{homeData.occupancy}</span>
                                <span className="pulse-trend trend-up"><i className="fas fa-caret-up"></i> 5%</span>
                            </div>
                            <div className="pulse-mini-card">
                                <span className="pulse-mini-label">Arrivi</span>
                                <span className="pulse-mini-value">{homeData.arrivals}</span>
                                <span className="pulse-trend trend-down"><i className="fas fa-caret-down"></i> 2</span>
                            </div>
                        </div>

                        <div className="razer-mission-card">
                            <div className="mission-header">
                                <i className="fas fa-bolt-lightning"></i>
                                <span>Operational Cockpit</span>
                            </div>
                            <div className="mission-body">
                                <div className="priority-item">
                                    <span className="priority-label">Ticket Aperti</span>
                                    <span className="priority-value">{homeData.tickets}</span>
                                </div>
                                <div className="priority-item">
                                    <span className="priority-label">Alert Critici</span>
                                    <span className="priority-value text-danger">2</span>
                                </div>
                            </div>
                        </div>

                        <div className="razer-quick-activity">
                            <div className="razer-section-subtitle">Eventi Recenti</div>
                            <div className="activity-snippets">
                                {homeData.recentActivity.map((act, idx) => (
                                    <div key={idx} className="activity-snippet-item">
                                        <i className={`fas ${act.icon || 'fa-circle-dot'} neon-blue`}></i>
                                        <div className="snippet-content">
                                            <span className="snippet-text">{act.description}</span>
                                            <span className="snippet-time">Adesso</span>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>

                        <div className="razer-grid">
                            <div className="razer-app-card" onClick={() => setIsSearchOpen(true)}>
                                <div className="app-icon-box"><i className="fas fa-search"></i></div>
                                <div className="app-name">Cerca Funzione</div>
                            </div>
                            <div className="razer-app-card" onClick={() => setActiveTab('launcher')}>
                                <div className="app-icon-box"><i className="fas fa-th-large"></i></div>
                                <div className="app-name">Tutte le App</div>
                            </div>
                        </div>
                    </div>

                    {/* Status: Telemetry */}
                    <div className="razer-tab-page tab-status">
                        <div className="razer-section-title">Telemetry Hub</div>
                        <div className="razer-telemetry-grid">
                            <div className="telemetry-card">
                                <div className="telemetry-label">Ricavi del Giorno</div>
                                <div className="telemetry-value neon-blue">{homeData.revenue}</div>
                                <div className="neon-progress-container">
                                    <div className="neon-progress-bar blue" style={{ width: '85%' }}></div>
                                </div>
                            </div>
                            <div className="telemetry-card">
                                <div className="telemetry-label">Performance Team</div>
                                <div className="telemetry-value neon-green">94%</div>
                                <div className="neon-progress-container">
                                    <div className="neon-progress-bar green" style={{ width: '94%' }}></div>
                                </div>
                            </div>
                        </div>
                        <div className="razer-quick-widget">
                             <WidgetRenderer widgetId="system-pulse-widget" />
                        </div>
                    </div>

                    {/* Launcher: Apps Grid */}
                    <div className="razer-tab-page tab-launcher">
                        <div className="razer-section-title">Nuvia Apps</div>

                        {/* Recent Apps */}
                        {recentApps.length > 0 && (
                            <div className="razer-app-category">
                                <div className="category-label">
                                    <i className="fas fa-clock-rotate-left"></i>
                                    Recenti
                                </div>
                                <div className="razer-grid">
                                    {recentApps.map(appId => {
                                        const item = [...availableApps, ...availableWidgets].find(i => i.id === appId);
                                        if (!item) return null;
                                        return (
                                            <div
                                                key={`recent-${appId}`}
                                                className="razer-app-card"
                                                onClick={() => handleLaunchApp(appId)}
                                            >
                                                <div className="app-icon-box">
                                                    <i className={`fas ${item.icon}`}></i>
                                                </div>
                                                <div className="app-name">{item.name}</div>
                                            </div>
                                        );
                                    })}
                                </div>
                            </div>
                        )}

                        {/* Categorized Apps */}
                        {Object.entries(categorizedApps).map(([category, items]) => (
                            items.length > 0 && (
                                <div key={category} className="razer-app-category">
                                    <div className="category-label">
                                        <i className={`fas ${category === 'Management' ? 'fa-briefcase' : category === 'Operations' ? 'fa-gears' : 'fa-id-card'}`}></i>
                                        {category}
                                    </div>
                                    <div className="razer-grid">
                                        {items.map(item => (
                                            <div
                                                key={item.id}
                                                className="razer-app-card"
                                                onClick={() => handleLaunchApp(item.id)}
                                            >
                                                <div className="app-icon-box">
                                                    <i className={`fas ${item.icon}`}></i>
                                                </div>
                                                <div className="app-name">{item.name}</div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )
                        ))}
                    </div>

                    {/* Profile & Identity */}
                    <div className="razer-tab-page tab-profile">
                        <div className="razer-section-title">Identity</div>

                        <div className="razer-profile-card">
                            <div className="profile-avatar-box">
                                <img src="/static/img/avatar-placeholder.png" alt="Profile" onError={(e) => e.target.src = 'https://ui-avatars.com/api/?name=Admin&background=0ea5e9&color=fff'} />
                                <div className="profile-status-dot"></div>
                            </div>
                            <div className="profile-name">{document.body.dataset.userName || 'Amministratore'}</div>
                            <div className="profile-role">{document.body.dataset.userRole || 'Superuser'}</div>
                        </div>

                        <div className="profile-actions-grid">
                            <a href="/profile-cards/" className="profile-action-item">
                                <i className="fas fa-address-card"></i>
                                <div className="action-label-box">
                                    <span className="action-label-title">Digital Business Card</span>
                                    <span className="action-label-desc">Gestisci il tuo profilo pubblico</span>
                                </div>
                            </a>
                            <a href="/admin/password_change/" className="profile-action-item">
                                <i className="fas fa-shield-halved"></i>
                                <div className="action-label-box">
                                    <span className="action-label-title">Sicurezza</span>
                                    <span className="action-label-desc">Cambia password e 2FA</span>
                                </div>
                            </a>
                            <button className="profile-action-item" onClick={() => window.location.assign('/accounts/logout/')}>
                                <i className="fas fa-right-from-bracket" style={{color: '#ef4444'}}></i>
                                <div className="action-label-box">
                                    <span className="action-label-title" style={{color: '#ef4444'}}>Logout</span>
                                    <span className="action-label-desc">Termina la sessione</span>
                                </div>
                            </button>
                        </div>
                    </div>

                    {/* Multitask: Task Switcher */}
                    <div className="razer-tab-page tab-multitask">
                        <div className="razer-section-title">Sessioni Attive</div>
                        {openApps.length === 0 ? (
                            <div className="razer-empty-state">Nessuna app aperta.</div>
                        ) : (
                            <div className="task-list">
                                {openApps.map(appId => {
                                    const app = [...availableApps, ...availableWidgets].find(i => i.id === appId);
                                    return (
                                        <div key={appId} className="task-card">
                                            <div className="task-preview">
                                                <i className={`fas ${app.icon} fa-3x neon-blue`}></i>
                                            </div>
                                            <div className="task-footer">
                                                <span>{app.name}</span>
                                                <button className="btn-minimize-app" onClick={() => setActiveAppId(appId)}>
                                                    <i className="fas fa-arrow-up-right-from-square"></i>
                                                </button>
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        )}
                    </div>

                </div>
            </main>

            <nav className="razer-bottom-nav">
                <button className={`nav-item ${activeTab === 'home' ? 'active' : ''}`} onClick={() => setActiveTab('home')}>
                    <i className="fas fa-house-chimney"></i>
                    <span>Home</span>
                </button>
                <button className={`nav-item ${activeTab === 'status' ? 'active' : ''}`} onClick={() => setActiveTab('status')}>
                    <i className="fas fa-chart-bar"></i>
                    <span>Hub</span>
                </button>
                <button className={`nav-item ${activeTab === 'launcher' ? 'active' : ''}`} onClick={() => setActiveTab('launcher')}>
                    <i className="fas fa-th-large"></i>
                    <span>App</span>
                </button>
                <button className={`nav-item ${activeTab === 'profile' ? 'active' : ''}`} onClick={() => setActiveTab('profile')}>
                    <i className="fas fa-user-circle"></i>
                    <span>Me</span>
                </button>
                <button className={`nav-item ${activeTab === 'multitask' ? 'active' : ''}`} onClick={() => setActiveTab('multitask')}>
                    <i className="fas fa-layer-group"></i>
                    <span>Task</span>
                </button>
            </nav>

            <div className="razer-fab-container">
                <button className="razer-main-fab" onClick={() => setIsSearchOpen(true)}>
                    <i className="fas fa-magnifying-glass"></i>
                </button>
            </div>

            {/* Immersive App Shell */}
            {activeAppId && (
                <div className="razer-app-container">
                    <div className="razer-app-shell">
                        <div className="razer-app-header">
                            <div className="app-info">
                                <i className={`fas ${[...availableApps, ...availableWidgets].find(a => a.id === activeAppId)?.icon}`}></i>
                                <span>{[...availableApps, ...availableWidgets].find(a => a.id === activeAppId)?.name}</span>
                            </div>
                            <button className="btn-minimize-app" onClick={() => setActiveAppId(null)}>
                                <i className="fas fa-chevron-down"></i>
                            </button>
                        </div>
                        <iframe
                            src={`${[...availableApps, ...availableWidgets].find(a => a.id === activeAppId)?.url || '#'}${([...availableApps, ...availableWidgets].find(a => a.id === activeAppId)?.url?.includes('?') ? '&' : '?')}chromeless=true`}
                            className="razer-app-iframe"
                            frameBorder="0"
                            title="Nuvia App Container"
                        />
                        <div className="razer-home-bar" onClick={() => setActiveAppId(null)}></div>
                    </div>
                </div>
            )}

            {/* AI Search Overlay */}
            {isSearchOpen && (
                <div className="razer-mobile-search-overlay">
                    <div className="search-overlay-header">
                        <i className="fas fa-magnifying-glass neon-blue"></i>
                        <input
                            type="text"
                            placeholder="Cerca o chiedi a Nuvia..."
                            autoFocus
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                        />
                        <button className="btn-close-search" onClick={() => setIsSearchOpen(false)}>
                            <i className="fas fa-xmark"></i>
                        </button>
                    </div>
                    <div className="search-overlay-results custom-scrollbar">
                        {aiCommands.map(cmd => (
                            <button key={cmd.id} className="search-result-item" onClick={() => handleCommandAction(cmd)}>
                                <i className={`fas ${cmd.icon}`}></i>
                                <div className="res-details">
                                    <div className="res-name"><span className="command-tag">AI</span> {cmd.name}</div>
                                    <div className="res-type">{cmd.description}</div>
                                </div>
                            </button>
                        ))}
                        {availableApps.filter(i => i.name.toLowerCase().includes(searchQuery.toLowerCase())).map(app => (
                            <button key={app.id} className="search-result-item" onClick={() => handleLaunchApp(app.id)}>
                                <i className={`fas ${app.icon}`}></i>
                                <div className="res-details">
                                    <div className="res-name">{app.name}</div>
                                    <div className="res-type">Applicazione</div>
                                </div>
                            </button>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
};

export default MobileOS;
