const sanitizeLabel = (text = '') => text.replace(/\s+/g, ' ').trim();

const computeDepth = (element) => {
    let depth = 0;
    let current = element?.parentElement || null;

    while (current) {
        if (current.classList?.contains('collapse')) {
            depth += 1;
        }
        current = current.parentElement;
    }

    return depth;
};

const extractIconClass = (link) => {
    const iconElement = link?.querySelector?.('i');
    if (!iconElement) {
        return 'fas fa-circle';
    }
    return iconElement.className || 'fas fa-circle';
};

export const SIDEBAR_CONTAINER_SELECTOR = '#sidebarMenu .sidebar-nav-container';

export const collectSidebarMenuItems = (sidebarRoot) => {
    if (!sidebarRoot) {
        return [];
    }

    const rawLinks = Array.from(sidebarRoot.querySelectorAll('a.nav-link'));

    const items = rawLinks
        .map((link) => {
            const href = link.getAttribute('href');

            if (!href || href.startsWith('#')) {
                return null;
            }

            return {
                href,
                label: sanitizeLabel(link.textContent || ''),
                iconClass: extractIconClass(link),
                isActive: link.classList.contains('active') || link.classList.contains('active-sub-link'),
                depth: computeDepth(link),
            };
        })
        .filter(Boolean);

    const seen = new Set();
    const deduped = [];

    for (const item of items) {
        const key = `${item.href}|${item.label}`;
        if (!seen.has(key)) {
            seen.add(key);
            deduped.push(item);
        }
    }

    return deduped;
};
