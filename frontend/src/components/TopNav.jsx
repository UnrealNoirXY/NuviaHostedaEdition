import React from 'react';
import './TopNav.css';

const NAV_LINKS = [
    { id: 'desk', label: 'Desk', href: '/desk/' },
    { id: 'bookings', label: 'Bookings', href: '/bookings/dashboard/' },
    { id: 'economato', label: 'Economato', href: '/economato/app/' },
    { id: 'analysis', label: 'Analysis', href: '/reviews/analysis-center/' },
];

const getDataset = () => {
    if (typeof document === 'undefined') {
        return {};
    }

    return document.body?.dataset || {};
};

const normalizePath = (path) => {
    if (!path) {
        return '/';
    }

    const normalized = path.endsWith('/') ? path : `${path}/`;
    return normalized.startsWith('/') ? normalized : `/${normalized}`;
};

const TopNav = ({ currentPath }) => {
    const { hubUrl, logoUrl } = getDataset();
    const resolvedPath = currentPath || (typeof window !== 'undefined' ? window.location.pathname : '/');
    const normalizedPath = normalizePath(resolvedPath);
    const brandHref = hubUrl || '/';

    return (
        <nav className="top-nav" aria-label="Navigazione principale">
            <a className="top-nav__brand" href={brandHref} aria-label="Vai alla Home">
                {logoUrl ? (
                    <img className="top-nav__logo" src={logoUrl} alt="Nuvia" />
                ) : (
                    <span className="top-nav__logo-fallback" aria-hidden="true" />
                )}
                <span className="top-nav__title">Nuvia OS</span>
            </a>
            <div className="top-nav__links" role="menubar">
                {NAV_LINKS.map((link) => {
                    const normalizedLink = normalizePath(link.href);
                    const isActive = normalizedPath.startsWith(normalizedLink);

                    return (
                        <a
                            key={link.id}
                            className={`top-nav__link ${isActive ? 'is-active' : ''}`}
                            href={link.href}
                            role="menuitem"
                            aria-current={isActive ? 'page' : undefined}
                        >
                            {link.label}
                        </a>
                    );
                })}
            </div>
        </nav>
    );
};

export default TopNav;
