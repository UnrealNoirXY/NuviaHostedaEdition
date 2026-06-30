/* eslint-disable no-restricted-globals */
import { clientsClaim } from 'workbox-core';
import { precacheAndRoute } from 'workbox-precaching';
import { registerRoute } from 'workbox-routing';
import { NetworkFirst, CacheFirst, StaleWhileRevalidate } from 'workbox-strategies';

self.skipWaiting();
clientsClaim();

const PRECACHE_ENTRIES = self.__WB_MANIFEST || [];
precacheAndRoute(PRECACHE_ENTRIES);

const CACHE_NAMES = {
    publicPages: 'nuvia-public-pages',
    media: 'nuvia-media',
    assets: 'nuvia-assets',
};

const PUBLIC_PAGE_PREFIXES = ['/landing', '/login', '/reset-password', '/offline'];
const DEFAULT_SAFE_URL = new URL('/hub/', self.location.origin).toString();
const ALLOWED_EXTERNAL_NOTIFICATION_HOSTS = [];

const getFingerprintedAsset = (keywords, fallback) => {
    const entry = PRECACHE_ENTRIES.find(({ url }) => keywords.some((keyword) => url.includes(keyword)));
    if (!entry) {
        return fallback;
    }
    return new URL(entry.url, self.location.origin).toString();
};

const sanitizeSameOriginUrl = (rawUrl) => {
    if (!rawUrl) {
        return null;
    }
    try {
        const parsed = new URL(rawUrl, self.location.origin);
        if (parsed.origin === self.location.origin || ALLOWED_EXTERNAL_NOTIFICATION_HOSTS.includes(parsed.host)) {
            return parsed.toString();
        }
        return null;
    } catch (error) {
        return null;
    }
};

const resolveNotificationTarget = (rawUrl) => sanitizeSameOriginUrl(rawUrl) || DEFAULT_SAFE_URL;

const DEFAULT_NOTIFICATION_ICON = getFingerprintedAsset(['logo', 'icon'], '/static/img/logo.png');
const DEFAULT_NOTIFICATION_BADGE = getFingerprintedAsset(['badge', 'logo'], '/static/img/logo.png');
const PAGE_CACHE_KEYS = [CACHE_NAMES.publicPages, 'nuvia-pages'];

const offlineFallbackResponse = new Response(
    `<!doctype html>
<html lang="it">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Offline</title>
  <style>
    :root { color-scheme: light dark; }
    body { font-family: system-ui, -apple-system, "Segoe UI", sans-serif; margin: 0; padding: 2rem; }
    main { max-width: 32rem; margin: 0 auto; }
    h1 { margin-bottom: 0.5rem; }
    p { line-height: 1.6; }
  </style>
</head>
<body>
  <main>
    <h1>Sei offline</h1>
    <p>Non è possibile caricare la pagina richiesta senza connessione. Riprova quando torni online.</p>
  </main>
</body>
</html>`,
    {
        status: 503,
        headers: { 'Content-Type': 'text/html; charset=utf-8' },
    },
);

const isNavigationRequest = ({ request }) =>
    request.mode === 'navigate' || request.destination === 'document';

const isSameOriginNavigation = (url) => url.origin === self.location.origin;

const isPublicPath = (url) =>
    PUBLIC_PAGE_PREFIXES.some((prefix) => url.pathname === prefix || url.pathname.startsWith(`${prefix}/`));

const publicPageStrategy = new NetworkFirst({
    cacheName: CACHE_NAMES.publicPages,
    networkTimeoutSeconds: 10,
});

const handlePublicNavigation = async ({ event }) => {
    try {
        const response = await publicPageStrategy.handle({ event });
        if (response) {
            return response;
        }
    } catch (error) {
        // Fallback handled below
    }
    return offlineFallbackResponse;
};

const handleProtectedNavigation = async ({ event }) => {
    try {
        const response = await fetch(event.request, { cache: 'no-store' });
        if (response) {
            return response;
        }
    } catch (error) {
        // Return a minimal response while offline for protected pages
    }
    return new Response('Contenuto protetto non disponibile offline. Riprova quando sei online.', {
        status: 503,
        headers: { 'Content-Type': 'text/plain; charset=utf-8' },
    });
};

registerRoute(
    ({ request, url }) => isNavigationRequest({ request }) && isSameOriginNavigation(url) && isPublicPath(url),
    handlePublicNavigation,
);

registerRoute(
    ({ request, url }) => isNavigationRequest({ request }) && isSameOriginNavigation(url) && !isPublicPath(url),
    handleProtectedNavigation,
);

registerRoute(
    ({ request }) => request.destination === 'image',
    new CacheFirst({
        cacheName: CACHE_NAMES.media,
        matchOptions: { ignoreVary: true, ignoreSearch: true },
        fetchOptions: {
            credentials: 'same-origin',
        },
    }),
);

registerRoute(
    ({ request }) => ['script', 'style'].includes(request.destination),
    new StaleWhileRevalidate({
        cacheName: CACHE_NAMES.assets,
    }),
);

self.addEventListener('push', (event) => {
    if (!event.data) {
        return;
    }

    let payload;
    try {
        payload = event.data.json();
    } catch (error) {
        payload = { title: 'Aggiornamento', body: event.data.text() };
    }

    const title = payload.title || 'Notifica';
    const targetUrl = resolveNotificationTarget(payload.url || payload.cta_url || '/');
    const options = {
        body: payload.body || '',
        icon: sanitizeSameOriginUrl(payload.icon) || DEFAULT_NOTIFICATION_ICON,
        data: {
            url: targetUrl,
        },
        badge: sanitizeSameOriginUrl(payload.badge) || DEFAULT_NOTIFICATION_BADGE,
        tag: payload.tag || 'nuvia-notification',
        requireInteraction: payload.priority === 'urgent',
    };

    event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener('notificationclick', (event) => {
    event.notification.close();
    const destination = resolveNotificationTarget(event.notification.data?.url);

    event.waitUntil(
        clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clientList) => {
            for (const client of clientList) {
                if (client.url === destination && 'focus' in client) {
                    return client.focus();
                }
            }
            if (clients.openWindow) {
                return clients.openWindow(destination);
            }
            return null;
        }),
    );
});

const clearPageCaches = async (cacheKeys = PAGE_CACHE_KEYS) => {
    const keys = await caches.keys();
    const cacheKeysToDelete = keys.filter((key) => cacheKeys.includes(key));
    return Promise.all(cacheKeysToDelete.map((key) => caches.delete(key)));
};

self.addEventListener('message', (event) => {
    const messageType = event.data?.type || event.data;
    if (messageType === 'LOGOUT' || messageType === 'CLEAR_AUTH_STATE') {
        event.waitUntil(clearPageCaches());
    }
});

self.addEventListener('activate', (event) => {
    event.waitUntil(clearPageCaches(['nuvia-pages']));
});
