import React, { useEffect, useCallback } from 'react';
import PropTypes from 'prop-types';

const WidgetGallery = ({ availableWidgets, currentWidgetIds, onAddWidget, onClose }) => {
    const widgetsToAdd = availableWidgets.filter(
        (widget) => !currentWidgetIds.includes(widget.id)
    );

    const handleOverlayClick = (event) => {
        event.stopPropagation();
        onClose();
    };

    const handleKeyDown = useCallback((event) => {
        if (event.key === 'Escape') {
            onClose();
        }
    }, [onClose]);

    useEffect(() => {
        document.addEventListener('keydown', handleKeyDown);
        return () => {
            document.removeEventListener('keydown', handleKeyDown);
        };
    }, [handleKeyDown]);

    return (
        <div
            className="widget-popup-overlay"
            role="dialog"
            aria-modal="true"
            aria-labelledby="widget-gallery-title"
            onClick={handleOverlayClick}
        >
            <div className="widget-popup" onClick={(event) => event.stopPropagation()}>
                <div className="widget-popup-header">
                    <div>
                        <p className="widget-popup-eyebrow">Libreria widget</p>
                        <h3 id="widget-gallery-title">Aggiungi un widget</h3>
                    </div>
                    <button
                        onClick={onClose}
                        className="btn btn-sm btn-outline-light"
                        aria-label="Chiudi la galleria"
                        type="button"
                    >
                        <i className="fas fa-times"></i>
                    </button>
                </div>
                <div className="widget-popup-body">
                    {widgetsToAdd.length > 0 ? (
                        <div className="widget-gallery-list" role="list">
                            {widgetsToAdd.map((widget) => (
                                <button
                                    key={widget.id}
                                    type="button"
                                    className="widget-gallery-item"
                                    onClick={() => onAddWidget(widget.id)}
                                    role="listitem"
                                >
                                    <span className="widget-info">
                                        <i className={`${widget.icon || 'fas fa-puzzle-piece'} fa-fw`}></i>
                                        <span className="widget-name">{widget.name}</span>
                                    </span>
                                    <span className="widget-meta">
                                        <i className="fas fa-plus"></i>
                                        Inserisci
                                    </span>
                                </button>
                            ))}
                        </div>
                    ) : (
                        <div className="widget-gallery-empty">
                            <i className="fas fa-check-circle"></i>
                            <p>Tutti i widget disponibili sono già presenti sulla dashboard.</p>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

WidgetGallery.propTypes = {
    availableWidgets: PropTypes.arrayOf(
        PropTypes.shape({
            id: PropTypes.oneOfType([PropTypes.string, PropTypes.number]).isRequired,
            name: PropTypes.string.isRequired,
            icon: PropTypes.string,
        })
    ).isRequired,
    currentWidgetIds: PropTypes.arrayOf(
        PropTypes.oneOfType([PropTypes.string, PropTypes.number])
    ).isRequired,
    onAddWidget: PropTypes.func.isRequired,
    onClose: PropTypes.func.isRequired,
};

export default WidgetGallery;
