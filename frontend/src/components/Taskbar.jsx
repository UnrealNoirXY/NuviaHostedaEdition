import React, { useState, useEffect } from 'react';

const Taskbar = ({ windows, focusedWindowId, onRestore, onFocus, onMinimize, onClose, onLaunch, onOpenLauncher, onOpenNotifications, pinnedApps = [], availableWidgets = [], availableApps = [], onPin, onUnpin, onContextMenu, workspaces = [], activeWorkspaceId = 0, onWorkspaceChange }) => {
    const [currentTime, setCurrentTime] = useState(new Date());

    useEffect(() => {
        const timer = setInterval(() => setCurrentTime(new Date()), 10000);
        return () => clearInterval(timer);
    }, []);

    // Mostriamo le app fissate + le app attualmente aperte che non sono fissate
    const openAppIds = windows.map(w => w.id);
    const uniqueAppIds = Array.from(new Set([...pinnedApps, ...openAppIds]));

    const findItem = (id) => {
        return availableWidgets.find(w => w.id === id) || availableApps.find(a => a.id === id);
    };

    const getIconForId = (id) => {
        const win = windows.find(w => w.id === id);
        if (win) return win.icon;
        const item = findItem(id);
        return item ? item.icon : 'fa-window-maximize';
    };

    const getTitleForId = (id) => {
        const win = windows.find(w => w.id === id);
        if (win) return win.title;
        const item = findItem(id);
        return item ? item.name : 'Applicazione';
    };

    return (
        <div className="nuvia-taskbar-container">
            <div className="taskbar-dock glass">
                <div className="taskbar-start-section">
                    <button
                        className="taskbar-item taskbar-start-button"
                        onClick={onOpenLauncher}
                        title="Launcher Nuvia OS"
                    >
                        <i className="fas fa-th-large"></i>
                    </button>
                </div>

                <div className="taskbar-workspaces-section">
                    {workspaces.map(ws => (
                        <button
                            key={ws.id}
                            className={`workspace-tab ${activeWorkspaceId === ws.id ? 'is-active' : ''}`}
                            onClick={() => onWorkspaceChange(ws.id)}
                            onContextMenu={(e) => {
                                e.preventDefault();
                                onContextMenu(e, [
                                    {
                                        label: `Rinomina ${ws.name}`,
                                        icon: 'fa-edit',
                                        onClick: () => {
                                            const newName = prompt('Nuovo nome per lo spazio di lavoro:', ws.name);
                                            if (newName) onWorkspaceChange({ type: 'rename', id: ws.id, name: newName });
                                        }
                                    },
                                    {
                                        label: 'Elimina Spazio',
                                        icon: 'fa-trash-alt',
                                        onClick: () => {
                                            if (workspaces.length > 1 && confirm('Sei sicuro di voler eliminare questo spazio di lavoro? Tutte le sue finestre verranno chiuse.')) {
                                                onWorkspaceChange({ type: 'delete', id: ws.id });
                                            }
                                        }
                                    }
                                ]);
                            }}
                            title={ws.name}
                        >
                            {ws.id + 1}
                        </button>
                    ))}
                    <button className="workspace-tab add-ws" onClick={() => onWorkspaceChange(-1)} title="Nuovo Spazio">
                        <i className="fas fa-plus"></i>
                    </button>
                </div>

                <div className="taskbar-apps-section custom-scrollbar-h">
                    {uniqueAppIds.map(appId => {
                        const win = windows.find(w => w.id === appId);
                        const isActive = focusedWindowId === appId;
                        const isOpened = !!win;
                        const isPinned = pinnedApps.includes(appId);

                        return (
                            <button
                                key={appId}
                                className={`taskbar-item taskbar-app-button ${isActive ? 'is-active' : ''} ${win?.isMinimized ? 'is-minimized' : ''} ${!isOpened ? 'is-not-opened' : ''}`}
                                onClick={() => {
                                    if (!isOpened) {
                                        onLaunch(appId);
                                        return;
                                    }
                                    if (win.isMinimized) {
                                        onRestore(appId);
                                    } else {
                                        onFocus(appId);
                                    }
                                }}
                                onContextMenu={(e) => {
                                    e.preventDefault();
                                    const options = [];
                                    if (isOpened) options.push({ label: 'Chiudi', icon: 'fa-times-circle', onClick: () => onClose(appId) });
                                    if (isPinned) {
                                        options.push({ label: 'Rimuovi dalla barra', icon: 'fa-thumbtack', onClick: () => onUnpin(appId) });
                                    } else {
                                        options.push({ label: 'Fissa sulla barra', icon: 'fa-thumbtack', onClick: () => onPin(appId) });
                                    }
                                    onContextMenu(e, options);
                                }}
                                title={getTitleForId(appId)}
                            >
                                <i className={`fas ${getIconForId(appId)}`}></i>
                                {isOpened && <div className="app-indicator"></div>}
                            </button>
                        );
                    })}
                </div>

                <div className="taskbar-system-section">
                    <div className="system-tray">
                        <button
                            className="tray-item"
                            onClick={onOpenNotifications}
                            title="Notifiche e Attività"
                        >
                            <i className="fas fa-bell"></i>
                        </button>
                        <div className="tray-divider"></div>
                        <div className="time-display" title={currentTime.toLocaleDateString('it-IT', { weekday: 'long', day: '2-digit', month: 'long', year: 'numeric' })}>
                            <span className="time-value">
                                {currentTime.toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit' })}
                            </span>
                            <span className="date-value">
                                {currentTime.toLocaleDateString('it-IT', { day: '2-digit', month: '2-digit' })}
                            </span>
                        </div>
                    </div>
                    <button
                        className="show-desktop-btn"
                        title="Mostra Scrivania"
                        onClick={() => {
                            const allMinimized = windows.every(w => w.isMinimized);
                            windows.forEach(w => {
                                if (allMinimized) {
                                    onRestore(w.id);
                                } else if (!w.isMinimized) {
                                    onMinimize(w.id);
                                }
                            });
                        }}
                    ></button>
                </div>
            </div>
        </div>
    );
};

export default Taskbar;
