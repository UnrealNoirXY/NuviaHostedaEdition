import React from 'react';
import { Rnd } from 'react-rnd';

const Window = ({
    id,
    title,
    children,
    x,
    y,
    width,
    height,
    zIndex,
    isFocused,
    onFocus,
    onClose,
    onMinimize,
    onMaximize,
    onMove,
    onResize,
    isMaximized = false,
    icon = 'fa-window-maximize',
    type = 'widget',
    url = null
}) => {
    const isApp = type === 'app';

    return (
        <Rnd
            size={isMaximized ? { width: '100%', height: 'calc(100% - 32px)' } : { width, height }}
            position={isMaximized ? { x: 0, y: 32 } : { x, y }}
            onDragStop={(e, d) => !isMaximized && onMove(id, d.x, d.y)}
            onResizeStop={(e, direction, ref, delta, position) => {
                !isMaximized && onResize(id, ref.style.width, ref.style.height, position.x, position.y);
            }}
            dragHandleClassName="window-header"
            minWidth={300}
            minHeight={200}
            bounds="parent"
            disableDragging={isMaximized}
            enableResizing={!isMaximized}
            style={{ zIndex }}
        >
            <div
                className={`noir-window ${isFocused ? 'window-focused' : ''} ${isMaximized ? 'window-maximized' : ''}`}
                onClick={() => onFocus(id)}
            >
                <div className="window-header">
                    <div className="window-header-info">
                        <i className={`fas ${icon} window-icon`}></i>
                        <span className="window-title">{title}</span>
                    </div>
                    <div className="window-controls">
                        <button className="btn-window control-minimize" onClick={(e) => { e.stopPropagation(); onMinimize(id); }} title="Minimizza">
                            <i className="fas fa-minus"></i>
                        </button>
                        <button className="btn-window control-maximize" onClick={(e) => { e.stopPropagation(); onMaximize(id); }} title={isMaximized ? "Ripristina" : "Ingrandisci"}>
                            <i className={`fas ${isMaximized ? 'fa-compress-alt' : 'fa-expand-alt'}`}></i>
                        </button>
                        <button className="btn-window control-close" onClick={(e) => { e.stopPropagation(); onClose(id); }} title="Chiudi">
                            <i className="fas fa-times"></i>
                        </button>
                    </div>
                </div>
                <div className={`window-content ${isApp ? 'window-content-app' : ''}`}>
                    {isApp && url ? (
                        <iframe
                            src={`${url}${url.includes('?') ? '&' : '?'}chromeless=true`}
                            title={title}
                            className="app-iframe"
                            frameBorder="0"
                        />
                    ) : children}
                </div>
                <div className="window-glass-overlay"></div>
            </div>
        </Rnd>
    );
};

export default Window;
