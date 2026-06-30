import React, { useEffect, useRef } from 'react';
import PropTypes from 'prop-types';

const DEFAULT_ICON = 'fas fa-chevron-right';

const MobileMenuSheet = ({ open, onClose, menuItems }) => {
    const sheetRef = useRef(null);

    useEffect(() => {
        if (!open) {
            return undefined;
        }

        const previousOverflow = document.body.style.overflow;
        document.body.style.overflow = 'hidden';

        const handleKeyDown = (event) => {
            if (event.key === 'Escape') {
                onClose();
            }
        };

        document.addEventListener('keydown', handleKeyDown);

        return () => {
            document.body.style.overflow = previousOverflow;
            document.removeEventListener('keydown', handleKeyDown);
        };
    }, [open, onClose]);

    useEffect(() => {
        if (!open || !sheetRef.current) {
            return;
        }

        const firstAction = sheetRef.current.querySelector('button');
        if (firstAction) {
            firstAction.focus({ preventScroll: true });
        }
    }, [open]);

    if (!open) {
        return null;
    }

    const handleNavigate = (href) => {
        onClose();
        window.location.assign(href);
    };

    return (
        <div className="mobile-menu-overlay" role="dialog" aria-modal="true" aria-label="Navigazione rapida">
            <button
                type="button"
                className="mobile-menu-backdrop"
                onClick={onClose}
                aria-label="Chiudi menu"
            ></button>
            <div className="mobile-menu-sheet" ref={sheetRef}>
                <div className="mobile-menu-header">
                    <div className="mobile-menu-handle" aria-hidden="true"></div>
                    <div className="mobile-menu-title">
                        <span>Navigazione</span>
                        <button type="button" className="mobile-menu-close" onClick={onClose} aria-label="Chiudi menu">
                            <i className="fas fa-xmark" aria-hidden="true"></i>
                        </button>
                    </div>
                </div>
                <div className="mobile-menu-content">
                    {menuItems.length === 0 ? (
                        <p className="mobile-menu-empty">Nessuna voce di menu disponibile.</p>
                    ) : (
                        <ul className="mobile-menu-list">
                            {menuItems.map((item) => (
                                <li key={`${item.href}-${item.label}`} className={`mobile-menu-item depth-${item.depth}`}>
                                    <button
                                        type="button"
                                        className="mobile-menu-action"
                                        onClick={() => handleNavigate(item.href)}
                                    >
                                        <span className="mobile-menu-icon" aria-hidden="true">
                                            <i className={item.iconClass || DEFAULT_ICON}></i>
                                        </span>
                                        <span className="mobile-menu-label">{item.label}</span>
                                        {item.isActive && (
                                            <span className="mobile-menu-active" aria-hidden="true">
                                                <i className="fas fa-circle"></i>
                                            </span>
                                        )}
                                    </button>
                                </li>
                            ))}
                        </ul>
                    )}
                </div>
            </div>
        </div>
    );
};

MobileMenuSheet.propTypes = {
    open: PropTypes.bool.isRequired,
    onClose: PropTypes.func.isRequired,
    menuItems: PropTypes.arrayOf(
        PropTypes.shape({
            href: PropTypes.string.isRequired,
            label: PropTypes.string.isRequired,
            iconClass: PropTypes.string,
            isActive: PropTypes.bool,
            depth: PropTypes.number,
        }),
    ),
};

MobileMenuSheet.defaultProps = {
    menuItems: [],
};

export default MobileMenuSheet;
