import React, { useEffect, useState, useRef } from 'react';

const ContextMenu = ({ x, y, options, onClose }) => {
    const menuRef = useRef(null);

    useEffect(() => {
        const handleClickOutside = (event) => {
            if (menuRef.current && !menuRef.current.contains(event.target)) {
                onClose();
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, [onClose]);

    return (
        <div
            className="noir-context-menu glass"
            style={{ top: y, left: x }}
            ref={menuRef}
        >
            <ul className="context-menu-list">
                {options.map((opt, idx) => (
                    opt.separator ? (
                        <li key={idx} className="context-menu-separator"></li>
                    ) : (
                        <li
                            key={idx}
                            className="context-menu-item"
                            onClick={() => { opt.onClick(); onClose(); }}
                        >
                            <i className={`fas ${opt.icon} context-icon`}></i>
                            <span className="context-label">{opt.label}</span>
                        </li>
                    )
                ))}
            </ul>
        </div>
    );
};

export default ContextMenu;
