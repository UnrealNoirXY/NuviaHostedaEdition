import React from 'react';

const NoirWidgetWrapper = ({ title, icon, actions = [], children }) => {
    return (
        <div className="noir-app-container">
            <div className="noir-app-body">
                {children}
            </div>
            {actions.length > 0 && (
                <div className="noir-app-actions">
                    {actions.map((action, idx) => (
                        <button
                            key={idx}
                            className={`btn btn-sm ${action.variant || 'btn-outline-light'} noir-action-btn`}
                            onClick={action.onClick}
                        >
                            {action.icon && <i className={`fas ${action.icon} me-2`}></i>}
                            {action.label}
                        </button>
                    ))}
                </div>
            )}
        </div>
    );
};

export default NoirWidgetWrapper;
