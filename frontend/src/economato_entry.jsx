import React from 'react';
import ReactDOM from 'react-dom/client';
import EconomatoApp from './modules/economato/EconomatoApp';
import './pwa/registration';

const rootElement = document.getElementById('economato-root');

if (rootElement) {
    const { userRole, userName, userRoleLabel } = rootElement.dataset;
    const root = ReactDOM.createRoot(rootElement);
    root.render(
        <React.StrictMode>
            <EconomatoApp userRole={userRole} userRoleLabel={userRoleLabel} userName={userName} />
        </React.StrictMode>
    );
} else {
    console.error("Elemento radice '#economato-root' non trovato. L'app Economato non può essere montata.");
}
