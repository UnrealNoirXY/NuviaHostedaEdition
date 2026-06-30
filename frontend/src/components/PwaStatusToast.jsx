import React from 'react';
import PropTypes from 'prop-types';

const PwaStatusToast = ({
    offlineReady,
    needsRefresh,
    error,
    onRefresh,
    onDismiss,
}) => {
    const shouldShow = offlineReady || needsRefresh || !!error;

    if (!shouldShow) {
        return null;
    }

    const title = needsRefresh
        ? 'Aggiornamento disponibile'
        : offlineReady
            ? 'Pronto all\'uso offline'
            : 'Errore PWA';

    const message = error
        ? error
        : needsRefresh
            ? 'Ricarica per applicare le ultime ottimizzazioni della dashboard.'
            : 'Puoi continuare a utilizzare la piattaforma anche senza connessione.';

    const iconClass = error
        ? 'fa-triangle-exclamation'
        : needsRefresh
            ? 'fa-arrows-rotate'
            : 'fa-circle-check';

    return (
        <div className="pwa-toast" role="status" aria-live="polite">
            <div className="pwa-toast-inner">
                <div className="pwa-toast-icon" aria-hidden="true">
                    <i className={`fas ${iconClass}`}></i>
                </div>
                <div className="pwa-toast-body">
                    <p className="pwa-toast-title">{title}</p>
                    <p className="pwa-toast-message">{message}</p>
                </div>
                <div className="pwa-toast-actions">
                    {needsRefresh && (
                        <button type="button" className="btn btn-sm btn-primary" onClick={onRefresh}>
                            <i className="fas fa-rotate me-2"></i>
                            Aggiorna
                        </button>
                    )}
                    <button type="button" className="btn btn-sm btn-outline-light" onClick={onDismiss}>
                        Chiudi
                    </button>
                </div>
            </div>
        </div>
    );
};

PwaStatusToast.propTypes = {
    offlineReady: PropTypes.bool,
    needsRefresh: PropTypes.bool,
    error: PropTypes.string,
    onRefresh: PropTypes.func.isRequired,
    onDismiss: PropTypes.func.isRequired,
};

PwaStatusToast.defaultProps = {
    offlineReady: false,
    needsRefresh: false,
    error: null,
};

export default PwaStatusToast;
