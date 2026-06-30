import React, { useState, useEffect } from 'react';
import apiClient from '../apiClient';
import Window from './Window';
import WidgetRenderer from './WidgetRenderer';
import Taskbar from './Taskbar';
import ContextMenu from './ContextMenu';
import NotificationSidebar from './NotificationSidebar';
import SpotlightSearch from './SpotlightSearch';
import NuviaTour from './NuviaTour';
import SystemTopBar from './SystemTopBar';
import AppLauncher from './AppLauncher';

const Desktop = ({
    layouts = {},
    initialOpenWindows = [],
    initialPinnedIcons = [],
    initialWorkspaces = [],
    initialActiveWorkspaceId = 0,
    availableWidgets = [],
    availableApps = [],
    onLayoutChange,
    isGalleryOpen,
    setIsGalleryOpen,
    onAddWidget
}) => {
    const [wallpaper, setWallpaper] = useState(() => {
        return localStorage.getItem('nuvia_wallpaper') || 'noir-mesh';
    });
    const [windows, setWindows] = useState([]);
    const [pinnedApps, setPinnedApps] = useState(initialPinnedIcons || []);
    const [workspaces, setWorkspaces] = useState(initialWorkspaces || [{ id: 0, name: 'Principale' }]);
    const [activeWorkspaceId, setActiveWorkspaceId] = useState(initialActiveWorkspaceId || 0);
    const [focusedWindowId, setFocusedWindowId] = useState(null);
    const [zIndexCounter, setZIndexCounter] = useState(100);
    const [contextMenu, setContextMenu] = useState(null);
    const [isSidebarOpen, setIsSidebarOpen] = useState(false);
    const [isLauncherOpen, setIsLauncherOpen] = useState(false);
    const [isSearchOpen, setIsSearchOpen] = useState(false);
    const [isTourOpen, setIsTourOpen] = useState(() => {
        return !localStorage.getItem('nuvia_tour_completed');
    });
    const [activeAlerts, setActiveAlerts] = useState([]);
    const [focusMode, setFocusMode] = useState(false);
    const [backgroundWidgets, setBackgroundWidgets] = useState(() => {
        const stored = localStorage.getItem('nuvia_background_widgets');
        return stored ? JSON.parse(stored) : [];
    });

    // Fetch Smart Alerts and trigger Focus Mode
    // Handle Keyboard Shortcuts (CMD+K for Search)
    useEffect(() => {
        const handleKeyDown = (e) => {
            if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
                e.preventDefault();
                setIsSearchOpen(true);
            }
        };
        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, []);

    useEffect(() => {
        const checkAlerts = () => {
            apiClient.get('/api/desk/smart-alerts/')
                .then(res => {
                    setActiveAlerts(res.data);
                    if (res.data.length > 0) {
                        setFocusMode(true);
                        // Auto-launch target apps for critical alerts
                        res.data.forEach(alert => {
                            if (alert.level === 'critical') handleLaunch(alert.target_app);
                        });
                    } else {
                        setFocusMode(false);
                    }
                });
        };
        checkAlerts();
        const interval = setInterval(checkAlerts, 60000);
        return () => clearInterval(interval);
    }, []);

    // Initialize state from backend
    useEffect(() => {
        if (initialPinnedIcons) setPinnedApps(initialPinnedIcons);
    }, [initialPinnedIcons]);

    useEffect(() => {
        if (initialWorkspaces) setWorkspaces(initialWorkspaces);
    }, [initialWorkspaces]);

    useEffect(() => {
        if (initialActiveWorkspaceId !== undefined) setActiveWorkspaceId(initialActiveWorkspaceId);
    }, [initialActiveWorkspaceId]);

    useEffect(() => {
        if (initialOpenWindows && Array.isArray(initialOpenWindows) && initialOpenWindows.length > 0) {
            const restoredWindows = initialOpenWindows.map((winData, index) => {
                if (!winData) return null;
                const id = typeof winData === 'string' ? winData : winData.id;
                if (!id) return null;

                const widget = (availableWidgets || []).find(w => w && w.id === id);
                const app = (availableApps || []).find(a => a && a.id === id);

                if (!widget && !app) return null;
                const item = widget || app;
                const isApp = !!app;

                return {
                    id: item.id,
                    title: item.name,
                    x: winData.x ?? (100 + (index * 20)),
                    y: winData.y ?? (100 + (index * 20)),
                    width: winData.width ?? (isApp ? window.innerWidth * 0.8 : (item.w || 6) * 100),
                    height: winData.height ?? (isApp ? window.innerHeight * 0.8 : (item.h || 4) * 100),
                    zIndex: 100 + index,
                    isMinimized: false,
                    icon: item.icon || 'fa-window-maximize',
                    type: isApp ? 'app' : 'widget',
                    url: isApp ? item.url : null,
                    workspaceId: winData.workspaceId ?? 0
                };
            }).filter(Boolean);
            setWindows(restoredWindows);
        }
    }, [initialOpenWindows, availableWidgets]);

    // Synchronize state with backend (Debounced)
    useEffect(() => {
        const timer = setTimeout(() => {
            const windowStates = windows.map(w => ({
                id: w.id,
                x: w.x,
                y: w.y,
                width: w.width,
                height: w.height,
                workspaceId: w.workspaceId
            }));
            apiClient.post('/api/desk/layout/', {
                open_windows: windowStates,
                pinned_icons: pinnedApps,
                workspaces: workspaces,
                active_workspace_id: activeWorkspaceId
            }).catch(err => console.error("Error saving desktop state:", err));
            localStorage.setItem('nuvia_background_widgets', JSON.stringify(backgroundWidgets));
        }, 1000);
        return () => clearTimeout(timer);
    }, [windows, pinnedApps, workspaces, activeWorkspaceId, backgroundWidgets]);

    const findWidgetName = (widgetId) => {
        const widget = availableWidgets.find(w => w.id === widgetId);
        return widget ? widget.name : 'Applicazione';
    };

    const findWidgetIcon = (widgetId) => {
        const widget = availableWidgets.find(w => w.id === widgetId);
        return widget ? widget.icon : 'fa-window-maximize';
    };

    const handleFocus = (id) => {
        setFocusedWindowId(id);
        setZIndexCounter(prev => prev + 1);
        setWindows(prev => prev.map(w =>
            w.id === id ? { ...w, zIndex: zIndexCounter + 1 } : w
        ));
    };

    const handleClose = (id) => {
        setWindows(prev => prev.filter(w => w.id !== id));
        // Also trigger layout change for persistence if needed
    };

    const handleMinimize = (id) => {
        setWindows(prev => prev.map(w =>
            w.id === id ? { ...w, isMinimized: true } : w
        ));
    };

    const handleMaximize = (id) => {
        setWindows(prev => prev.map(w =>
            w.id === id ? { ...w, isMaximized: !w.isMaximized } : w
        ));
    };

    const handleMove = (id, x, y) => {
        setWindows(prev => prev.map(w =>
            w.id === id ? { ...w, x, y } : w
        ));
    };

    const handleResize = (id, width, height, x, y) => {
        setWindows(prev => prev.map(w =>
            w.id === id ? { ...w, width, height, x, y } : w
        ));
    };

    const handleRestore = (id) => {
        setWindows(prev => prev.map(w =>
            w.id === id ? { ...w, isMinimized: false } : w
        ));
        handleFocus(id);
    };

    const handleWorkspaceChange = (action) => {
        if (typeof action === 'number') {
            if (action === -1) {
                const nextId = workspaces.length > 0 ? Math.max(...workspaces.map(w => w.id)) + 1 : 0;
                setWorkspaces([...workspaces, { id: nextId, name: `Scrivania ${nextId + 1}` }]);
                setActiveWorkspaceId(nextId);
            } else {
                setActiveWorkspaceId(action);
            }
            return;
        }

        switch (action.type) {
            case 'rename':
                setWorkspaces(prev => prev.map(ws => ws.id === action.id ? { ...ws, name: action.name } : ws));
                break;
            case 'delete':
                setWindows(prev => prev.filter(w => w.workspaceId !== action.id));
                const filtered = workspaces.filter(ws => ws.id !== action.id);
                setWorkspaces(filtered);
                if (activeWorkspaceId === action.id) {
                    setActiveWorkspaceId(filtered.length > 0 ? filtered[0].id : 0);
                }
                break;
        }
    };

    const handleLaunch = (launchParam) => {
        if (!launchParam) return;
        const id = typeof launchParam === 'string' ? launchParam : (launchParam.id || launchParam.i);
        if (!id) return;

        const existingWindow = (windows || []).find(w => w && w.id === id);
        if (existingWindow) {
            handleRestore(id);
            return;
        }

        const widget = (availableWidgets || []).find(w => w && w.id === id);
        const app = (availableApps || []).find(a => a && a.id === id);

        if (!widget && !app) {
            console.warn(`Unknown launch target: ${id}`);
            return;
        }

        const item = widget || app;
        const isApp = !!app;

        const width = isApp ? Math.min(window.innerWidth * 0.85, 1400) : (item.w || 6) * 100;
        const height = isApp ? Math.min(window.innerHeight * 0.85, 900) : (item.h || 4) * 100;

        const newWindow = {
            id: item.id,
            title: item.name,
            x: isApp ? (window.innerWidth - width) / 2 : 100 + (windows.length * 20),
            y: isApp ? (window.innerHeight - height) / 2 : 100 + (windows.length * 20),
            width,
            height,
            zIndex: zIndexCounter + 1,
            isMinimized: false,
            icon: item.icon || 'fa-window-maximize',
            type: isApp ? 'app' : 'widget',
            url: isApp ? item.url : null,
            workspaceId: activeWorkspaceId
        };

        setWindows(prev => [...prev, newWindow]);
        setFocusedWindowId(widget.id);
        setZIndexCounter(prev => prev + 1);
    };

    const handleContextMenu = (e, options) => {
        e.preventDefault();
        setContextMenu({
            x: e.pageX,
            y: e.pageY,
            options
        });
    };

    const changeWallpaper = (type) => {
        setWallpaper(type);
        localStorage.setItem('nuvia_wallpaper', type);
    };

    const desktopOptions = [
        { label: 'Aggiungi Widget', icon: 'fa-plus-circle', onClick: () => setIsGalleryOpen(true) },
        { label: 'Nuova Manutenzione', icon: 'fa-screwdriver-wrench', onClick: () => window.location.assign('/maintenance/ticket/nuovo/') },
        { label: 'Ricerca Spotlight', icon: 'fa-search', onClick: () => setIsSearchOpen(true) },
        { label: 'Mostra Workflow', icon: 'fa-history', onClick: () => setIsSidebarOpen(true) },
        { separator: true },
        {
            label: 'Sfondo: Mesh',
            icon: 'fa-image',
            onClick: () => changeWallpaper('noir-mesh')
        },
        {
            label: 'Sfondo: Deep Blue',
            icon: 'fa-image',
            onClick: () => changeWallpaper('noir-blue')
        },
        {
            label: 'Sfondo: Obsidian',
            icon: 'fa-image',
            onClick: () => changeWallpaper('noir-obsidian')
        },
        { separator: true },
        { label: 'Impostazioni Desktop', icon: 'fa-cog', onClick: () => console.log('Settings...') }
    ];

    const userName = document.body.dataset.userName || 'Utente';
    const userRole = document.body.dataset.userRole || 'Staff';

    const handleDragOver = (e) => {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'copy';
    };

    const handleDropOnIcon = (e, targetAppId) => {
        e.preventDefault();
        const data = e.dataTransfer.getData('application/nuvia-context');
        if (data) {
            const context = JSON.parse(data);
            console.log(`Dropped context from ${context.source} into ${targetAppId}`, context);
            // Qui lanciamo l'app con i parametri (es. auto-popolamento)
            handleLaunch(targetAppId);
        }
    };

    return (
        <div
            className={`nuvia-desktop-layer ${focusMode ? 'desktop-focus-mode' : ''} wp-${wallpaper}`}
            onContextMenu={(e) => handleContextMenu(e, desktopOptions)}
            onDragOver={handleDragOver}
        >
            <SystemTopBar userName={userName} role={userRole} />
            <div className="desktop-background"></div>

            <div className="desktop-background-widgets">
                {backgroundWidgets.map(widgetId => {
                    const widget = availableWidgets.find(w => w.id === widgetId);
                    if (!widget) return null;
                    return (
                        <div key={widgetId} className="bg-widget-item glass">
                            <div className="bg-widget-header">
                                <i className={`fas ${widget.icon}`}></i>
                                <span>{widget.name}</span>
                                <button
                                    className="btn-close-sm"
                                    onClick={() => setBackgroundWidgets(prev => prev.filter(id => id !== widgetId))}
                                >
                                    <i className="fas fa-times"></i>
                                </button>
                            </div>
                            <div className="bg-widget-body">
                                <WidgetRenderer widgetId={widgetId} />
                            </div>
                        </div>
                    );
                })}
            </div>

            <div className="desktop-workspace">
                {activeAlerts.length > 0 && (
                    <div className="desktop-alert-banner glass">
                        <i className="fas fa-triangle-exclamation pulse-icon"></i>
                        <div className="alert-content">
                            <strong>{activeAlerts[0].title}</strong>: {activeAlerts[0].message}
                        </div>
                        <button className="btn btn-xs btn-primary" onClick={() => setFocusMode(false)}>Dismiss Focus</button>
                    </div>
                )}
                {windows.filter(w => !w.isMinimized && w.workspaceId === activeWorkspaceId).map(win => {
                    const hasAlert = activeAlerts.some(a => a.target_app === win.id);
                    return (
                        <Window
                            key={win.id}
                            {...win}
                            isFocused={focusedWindowId === win.id}
                            onFocus={handleFocus}
                            onClose={handleClose}
                            onMinimize={handleMinimize}
                            onMaximize={handleMaximize}
                            onMove={handleMove}
                            onResize={handleResize}
                            className={hasAlert ? 'window-alert-pulse' : ''}
                        >
                            <div className="desktop-app-container">
                                <WidgetRenderer widgetId={win.id} />
                            </div>
                        </Window>
                    );
                })}
            </div>

            {/* Desktop Icons */}
            <div className="desktop-icons">
                {availableWidgets.filter(w => pinnedApps.includes(w.id)).map(widget => (
                    <div
                        key={widget.id}
                        className="desktop-icon-item"
                        onDoubleClick={() => handleLaunch(widget.id)}
                        onContextMenu={(e) => {
                            e.stopPropagation();
                            const isBgPinned = backgroundWidgets.includes(widget.id);
                            handleContextMenu(e, [
                                { label: `Apri ${widget.name}`, icon: 'fa-external-link-alt', onClick: () => handleLaunch(widget.id) },
                                {
                                    label: isBgPinned ? 'Rimuovi dallo Sfondo' : 'Fissa sullo Sfondo',
                                    icon: 'fa-thumbtack',
                                    onClick: () => {
                                        if (isBgPinned) {
                                            setBackgroundWidgets(prev => prev.filter(id => id !== widget.id));
                                        } else {
                                            setBackgroundWidgets(prev => [...prev, widget.id]);
                                        }
                                    }
                                },
                                { label: 'Rimuovi dal Desktop', icon: 'fa-trash-alt', onClick: () => setPinnedApps(prev => prev.filter(id => id !== widget.id)) }
                            ]);
                        }}
                        onClick={(e) => {
                            if (window.innerWidth < 768) handleLaunch(widget.id);
                        }}
                        onDragOver={handleDragOver}
                        onDrop={(e) => handleDropOnIcon(e, widget.id)}
                    >
                        <div className="icon-wrapper glass">
                            <i className={`fas ${widget.icon}`}></i>
                        </div>
                        <span className="icon-label">{widget.name}</span>
                    </div>
                ))}
            </div>

            <Taskbar
                windows={windows.filter(w => w.workspaceId === activeWorkspaceId)}
                focusedWindowId={focusedWindowId}
                onRestore={handleRestore}
                onFocus={handleFocus}
                onMinimize={handleMinimize}
                onClose={handleClose}
                onLaunch={handleLaunch}
                onOpenLauncher={() => setIsLauncherOpen(true)}
                onOpenNotifications={() => setIsSidebarOpen(!isSidebarOpen)}
                pinnedApps={pinnedApps}
                availableWidgets={availableWidgets}
                availableApps={availableApps}
                onPin={(id) => setPinnedApps(prev => prev.includes(id) ? prev : [...prev, id])}
                onUnpin={(id) => setPinnedApps(prev => prev.filter(p => p !== id))}
                onContextMenu={handleContextMenu}
                workspaces={workspaces}
                activeWorkspaceId={activeWorkspaceId}
                onWorkspaceChange={handleWorkspaceChange}
            />

            <NotificationSidebar
                isOpen={isSidebarOpen}
                onClose={() => setIsSidebarOpen(false)}
                onAction={(event) => {
                    if (event.cta_url) window.location.assign(event.cta_url);
                }}
            />

            <SpotlightSearch
                isOpen={isSearchOpen}
                availableWidgets={availableWidgets}
                availableApps={availableApps}
                onClose={() => setIsSearchOpen(false)}
                onLaunch={(res) => {
                    handleLaunch(res.id);
                }}
            />

            <NuviaTour
                isOpen={isTourOpen}
                onComplete={() => {
                    localStorage.setItem('nuvia_tour_completed', 'true');
                    setIsTourOpen(false);
                }}
            />

            <AppLauncher
                isOpen={isLauncherOpen}
                onClose={() => setIsLauncherOpen(false)}
                availableWidgets={availableWidgets}
                availableApps={availableApps}
                onLaunch={handleLaunch}
                pinnedApps={pinnedApps}
                onPin={(id) => setPinnedApps(prev => prev.includes(id) ? prev : [...prev, id])}
            />

            {contextMenu && (
                <ContextMenu
                    {...contextMenu}
                    onClose={() => setContextMenu(null)}
                />
            )}
        </div>
    );
};

export default Desktop;
