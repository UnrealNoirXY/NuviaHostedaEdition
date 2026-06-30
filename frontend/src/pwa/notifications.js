import React from 'react';
import { createRoot } from 'react-dom/client';
import NotificationCenter from './components/NotificationCenter.jsx';

const SELECTOR = '[data-notification-center]';

const bootstrapNotifications = () => {
    document.querySelectorAll(SELECTOR).forEach((element) => {
        if (!element.__notificationRoot) {
            const root = createRoot(element);
            root.render(React.createElement(NotificationCenter, { mountNode: element }));
            element.__notificationRoot = root;
        }
    });
};

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bootstrapNotifications);
} else {
    bootstrapNotifications();
}
