import React from 'react';
import ReactDOM from 'react-dom/client';
import BookingsDashboard from './bookings_dashboard_main';
import './pwa/registration';

// Trova l'elemento radice nel template Django
const rootElement = document.getElementById('bookings-dashboard-root');

if (rootElement) {
    const root = ReactDOM.createRoot(rootElement);
    root.render(
        <React.StrictMode>
            <BookingsDashboard />
        </React.StrictMode>
    );
} else {
    console.error("Elemento radice '#bookings-dashboard-root' non trovato. L'app React non può essere montata.");
}