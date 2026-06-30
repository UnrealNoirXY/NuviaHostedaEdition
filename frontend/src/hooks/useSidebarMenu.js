import { useEffect, useState } from 'react';
import { collectSidebarMenuItems, SIDEBAR_CONTAINER_SELECTOR } from '../utils/sidebarMenu';

const serializeMenu = (items) => JSON.stringify(items);

const useSidebarMenu = () => {
    const [menuItems, setMenuItems] = useState([]);

    useEffect(() => {
        const container = document.querySelector(SIDEBAR_CONTAINER_SELECTOR);

        if (!container) {
            return undefined;
        }

        const updateMenu = () => {
            const nextItems = collectSidebarMenuItems(container);
            setMenuItems((prev) => {
                if (serializeMenu(prev) === serializeMenu(nextItems)) {
                    return prev;
                }
                return nextItems;
            });
        };

        updateMenu();

        const observer = new MutationObserver(updateMenu);
        observer.observe(container, {
            subtree: true,
            childList: true,
            attributes: true,
            attributeFilter: ['class'],
        });

        return () => observer.disconnect();
    }, []);

    return menuItems;
};

export default useSidebarMenu;
