import React from 'react';

const Widget = ({ title }) => {
    return (
        <div className="widget-container" style={{ padding: '1rem', height: '100%', overflow: 'auto' }}>
            <h5 className="widget-title">{title}</h5>
            <div className="widget-content">
                <p>Content for {title} will be loaded here.</p>
            </div>
        </div>
    );
};

export default Widget;
