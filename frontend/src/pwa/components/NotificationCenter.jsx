import React, {
    useCallback,
    useEffect,
    useMemo,
    useRef,
    useState,
} from 'react';
import { createPortal } from 'react-dom';
import apiClient from '../../apiClient';
import { ensurePwaRegistration } from '../registration';
import { addPwaListener } from '../events';

const AVATAR_SELECTOR = '[data-notification-avatar]';
const AVATAR_BADGE_SELECTOR = '[data-avatar-badge]';
const NOTIFICATION_VISIBLE_CLASS = 'app-topbar__notifications--visible';
const AVATAR_ALERT_CLASS = 'app-topbar__avatar--alert';
const FEED_REFRESH_MS = 60_000;
const SUMMARY_REFRESH_MS = 45_000;
const DATE_FORMATTER = new Intl.DateTimeFormat('it-IT', {
    dateStyle: 'short',
    timeStyle: 'short',
});

const formatDate = (value) => {
    if (!value) {
        return '';
    }

    try {
        const date = value instanceof Date ? value : new Date(value);
        return DATE_FORMATTER.format(date);
    } catch (error) {
        console.warn('Impossibile formattare la data', value, error);
        return String(value);
    }
};

const asBadgeValue = (count) => {
    if (!count) {
        return '';
    }
    return count > 99 ? '99+' : String(count);
};

const getDeviceType = () => {
    if (typeof navigator === 'undefined') {
        return 'web';
    }
    const ua = navigator.userAgent || '';
    if (/android/i.test(ua)) {
        return 'android';
    }
    if (/iphone|ipad|ipod/i.test(ua)) {
        return 'ios';
    }
    return 'web';
};

const urlBase64ToUint8Array = (base64String) => {
    const padding = '='.repeat((4 - (base64String.length % 4)) % 4);
    const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');

    const rawData = window.atob(base64);
    const outputArray = new Uint8Array(rawData.length);

    for (let i = 0; i < rawData.length; i += 1) {
        outputArray[i] = rawData.charCodeAt(i);
    }

    return outputArray;
};

const NotificationCenter = ({ mountNode }) => {
    const {
        feedUrl,
        summaryUrl,
        markAllUrl,
        markReadTemplate,
        subscriptionUrl,
    } = mountNode.dataset || {};

    const webPushPublicKey = document.body?.dataset?.webpushPublicKey || '';

    const [isOpen, setIsOpen] = useState(false);
    const [notifications, setNotifications] = useState([]);
    const [loading, setLoading] = useState(false);
    const [errorMessage, setErrorMessage] = useState('');
    const [unreadCount, setUnreadCount] = useState(0);
    const [showBell, setShowBell] = useState(false);
    const [panelPosition, setPanelPosition] = useState({
        top: 96,
        right: 24,
        maxHeight: 560,
        width: 360,
        alignment: 'below',
        isMobile: false,
        safeLeft: 0,
        safeRight: 0,
    });
    const [pushState, setPushState] = useState(() => {
        const supported = typeof window !== 'undefined'
            && 'Notification' in window
            && 'serviceWorker' in navigator;
        const permission = supported ? Notification.permission : 'denied';
        let status = 'idle';
        if (!supported) {
            status = 'unsupported';
        } else if (permission === 'granted') {
            status = 'enabled';
        } else if (permission === 'denied') {
            status = 'denied';
        }
        return {
            supported,
            permission,
            status,
            loading: false,
        };
    });

    const toggleButtonRef = useRef(null);
    const panelRef = useRef(null);
    const overlayContainerRef = useRef(null);
    const swRegistrationRef = useRef(null);
    const loadingRef = useRef(false);
    const avatarButtonRef = useRef(null);
    const avatarBadgeRef = useRef(null);

    const badgeValue = showBell && unreadCount > 0 ? asBadgeValue(unreadCount) : '';
    const panelId = 'appTopbarNotificationsPanel';

    useEffect(() => {
        avatarButtonRef.current = document.querySelector(AVATAR_SELECTOR);
        avatarBadgeRef.current = avatarButtonRef.current?.querySelector(AVATAR_BADGE_SELECTOR) || null;
        if (avatarBadgeRef.current) {
            avatarBadgeRef.current.hidden = true;
        }
        if (avatarButtonRef.current) {
            avatarButtonRef.current.dataset.notificationState = 'hidden';
        }
    }, []);

    useEffect(() => {
        const avatarButton = avatarButtonRef.current;
        const avatarBadge = avatarBadgeRef.current;
        if (!avatarButton) {
            return;
        }

        if (isOpen) {
            avatarButton.classList.remove(AVATAR_ALERT_CLASS);
            avatarButton.dataset.notificationState = 'open';
            if (avatarBadge) {
                avatarBadge.hidden = true;
            }
            return;
        }

        if (unreadCount > 0) {
            avatarButton.classList.add(AVATAR_ALERT_CLASS);
            avatarButton.dataset.notificationState = 'alert';
            if (avatarBadge) {
                avatarBadge.hidden = false;
                avatarBadge.textContent = asBadgeValue(unreadCount);
            }
        } else {
            avatarButton.classList.remove(AVATAR_ALERT_CLASS);
            avatarButton.dataset.notificationState = showBell ? 'revealed' : 'hidden';
            if (avatarBadge) {
                avatarBadge.hidden = true;
            }
        }
    }, [isOpen, unreadCount, showBell]);

    useEffect(() => {
        const avatarButton = avatarButtonRef.current;
        if (!avatarButton) {
            return undefined;
        }

        const handleAvatarClick = (event) => {
            if (
                toggleButtonRef.current
                && (toggleButtonRef.current === event.target
                    || toggleButtonRef.current.contains(event.target))
            ) {
                return;
            }

            event.preventDefault();
            event.stopPropagation();
            if (typeof event.stopImmediatePropagation === 'function') {
                event.stopImmediatePropagation();
            }

            setShowBell((visible) => {
                if (visible) {
                    setIsOpen(false);
                    return false;
                }
                return true;
            });
        };

        avatarButton.addEventListener('click', handleAvatarClick, true);
        return () => {
            avatarButton.removeEventListener('click', handleAvatarClick, true);
        };
    }, []);

    useEffect(() => {
        if (!showBell) {
            return;
        }

        const focusToggle = () => {
            toggleButtonRef.current?.focus();
        };

        if (typeof window !== 'undefined' && typeof window.requestAnimationFrame === 'function') {
            window.requestAnimationFrame(focusToggle);
        } else {
            focusToggle();
        }
    }, [showBell]);

    useEffect(() => {
        if (!mountNode) {
            return;
        }
        if (showBell) {
            mountNode.classList.add(NOTIFICATION_VISIBLE_CLASS);
        } else {
            mountNode.classList.remove(NOTIFICATION_VISIBLE_CLASS);
        }
    }, [mountNode, showBell]);

    useEffect(() => {
        if (toggleButtonRef.current) {
            toggleButtonRef.current.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
        }
    }, [isOpen]);

    useEffect(() => {
        if (isOpen) {
            document.body?.classList.add('notification-center-open');
        } else {
            document.body?.classList.remove('notification-center-open');
        }
        return () => {
            document.body?.classList.remove('notification-center-open');
        };
    }, [isOpen]);

    useEffect(() => {
        const container = document.createElement('div');
        container.className = 'notifications-portal';
        document.body.appendChild(container);
        overlayContainerRef.current = container;
        return () => {
            container.remove();
            overlayContainerRef.current = null;
        };
    }, []);

    useEffect(() => {
        const container = overlayContainerRef.current;
        if (!container) {
            return;
        }
        if (isOpen) {
            container.classList.add('notifications-portal--open');
        } else {
            container.classList.remove('notifications-portal--open');
        }
    }, [isOpen]);

    useEffect(() => {
        const removeListener = addPwaListener((event) => {
            if (event?.type === 'registered' && event.registration) {
                swRegistrationRef.current = event.registration;
            }
        });
        return removeListener;
    }, []);

    useEffect(() => {
        if (!summaryUrl) {
            return undefined;
        }

        let isMounted = true;

        const fetchSummary = async () => {
            try {
                const response = await apiClient.get(summaryUrl);
                if (!isMounted) {
                    return;
                }
                const unread = response.data?.unread_count ?? 0;
                setUnreadCount(unread);
            } catch (error) {
                console.warn('Impossibile aggiornare il contatore notifiche', error);
            }
        };

        fetchSummary();
        const timer = window.setInterval(fetchSummary, SUMMARY_REFRESH_MS);
        return () => {
            isMounted = false;
            window.clearInterval(timer);
        };
    }, [summaryUrl]);

    const updatePanelPosition = useCallback(() => {
        const anchor = toggleButtonRef.current || avatarButtonRef.current || mountNode;
        if (!anchor || typeof window === 'undefined') {
            return;
        }

        const anchorRect = anchor.getBoundingClientRect();
        const viewportWidth = window.innerWidth || document.documentElement?.clientWidth || 0;
        const viewportHeight = window.innerHeight || document.documentElement?.clientHeight || 0;
        const visualViewport = window.visualViewport;
        const safeTop = visualViewport ? visualViewport.offsetTop : 0;
        const safeLeft = visualViewport ? visualViewport.offsetLeft : 0;
        const safeRight = visualViewport
            ? Math.max(viewportWidth - (visualViewport.width + safeLeft), 0)
            : 0;
        const safeBottom = visualViewport
            ? Math.max(viewportHeight - (visualViewport.height + safeTop), 0)
            : 0;
        const isMobileViewport = viewportWidth <= 767;
        const gap = 12;

        const panelElement = panelRef.current;
        const panelRect = panelElement && panelElement.hidden === false
            ? panelElement.getBoundingClientRect()
            : null;

        const fallbackWidth = isMobileViewport
            ? Math.max(
                  Math.min(viewportWidth - safeLeft - safeRight - gap * 2, 420),
                  300,
              )
            : Math.min(Math.max(viewportWidth * 0.3, 320), 420);
        const fallbackHeight = Math.min(Math.max(viewportHeight * 0.55, 360), 640);

        const panelWidth = panelRect?.width || fallbackWidth;
        const panelHeight = panelRect?.height || fallbackHeight;

        const bottomLimit = viewportHeight - safeBottom - gap;
        const dropDownTop = anchorRect.bottom + gap + safeTop;
        const dropUpTop = anchorRect.top - gap - panelHeight + safeTop;

        let top = dropDownTop;
        let alignment = 'below';

        if (dropDownTop + panelHeight > bottomLimit && dropUpTop >= safeTop + gap) {
            top = Math.min(dropUpTop, bottomLimit - panelHeight);
            alignment = 'above';
        }

        if (!Number.isFinite(top)) {
            top = safeTop + gap;
        }

        top = Math.max(
            Math.min(top, bottomLimit - Math.min(panelHeight, fallbackHeight)),
            safeTop + gap,
        );

        let right = viewportWidth - anchorRect.right - safeLeft;
        right = Math.max(right, gap + safeRight);
        const maxRight = Math.max(viewportWidth - safeLeft - panelWidth - gap, gap + safeRight);
        right = Math.min(right, maxRight);

        const availableSpace = Math.max(bottomLimit - top, 0);
        const fallbackMaxHeight = Math.min(panelHeight, fallbackHeight);
        const maxHeight = availableSpace > 0
            ? Math.max(
                  Math.min(availableSpace, 640),
                  Math.min(availableSpace, 280),
              )
            : fallbackMaxHeight;

        const mobileWidth = Math.max(
            Math.min(viewportWidth - safeLeft - safeRight - gap * 2, 420),
            300,
        );

        const nextPosition = {
            top,
            right,
            maxHeight,
            width: isMobileViewport ? mobileWidth : panelWidth,
            alignment,
            isMobile: isMobileViewport,
            safeLeft,
            safeRight,
        };

        setPanelPosition((previous) => {
            if (
                Math.abs(previous.top - nextPosition.top) < 0.5
                && Math.abs(previous.right - nextPosition.right) < 0.5
                && Math.abs(previous.maxHeight - nextPosition.maxHeight) < 0.5
                && Math.abs(previous.width - nextPosition.width) < 0.5
                && Math.abs(previous.safeLeft - nextPosition.safeLeft) < 0.5
                && Math.abs(previous.safeRight - nextPosition.safeRight) < 0.5
                && previous.alignment === nextPosition.alignment
                && previous.isMobile === nextPosition.isMobile
            ) {
                return previous;
            }
            return nextPosition;
        });
    }, [mountNode]);

    useEffect(() => {
        if (!showBell) {
            return;
        }

        const measure = () => {
            updatePanelPosition();
        };

        if (typeof window !== 'undefined' && typeof window.requestAnimationFrame === 'function') {
            window.requestAnimationFrame(measure);
        } else {
            measure();
        }
    }, [showBell, updatePanelPosition]);

    useEffect(() => {
        if (!isOpen) {
            return undefined;
        }
        updatePanelPosition();
        const handleScroll = () => updatePanelPosition();
        window.addEventListener('resize', updatePanelPosition);
        window.addEventListener('scroll', handleScroll, true);
        const viewport = typeof window !== 'undefined' ? window.visualViewport : undefined;
        if (viewport) {
            viewport.addEventListener('resize', updatePanelPosition);
            viewport.addEventListener('scroll', updatePanelPosition);
        }
        return () => {
            window.removeEventListener('resize', updatePanelPosition);
            window.removeEventListener('scroll', handleScroll, true);
            if (viewport) {
                viewport.removeEventListener('resize', updatePanelPosition);
                viewport.removeEventListener('scroll', updatePanelPosition);
            }
        };
    }, [isOpen, updatePanelPosition]);

    useEffect(() => {
        if (!isOpen) {
            return;
        }

        if (typeof window !== 'undefined' && typeof window.requestAnimationFrame === 'function') {
            const rafId = window.requestAnimationFrame(() => {
                updatePanelPosition();
            });
            return () => {
                if (window.cancelAnimationFrame) {
                    window.cancelAnimationFrame(rafId);
                }
            };
        }

        updatePanelPosition();
    }, [isOpen, notifications.length, loading, errorMessage, updatePanelPosition]);

    useEffect(() => {
        if (!isOpen) {
            return undefined;
        }
        const handleKeyDown = (event) => {
            if (event.key === 'Escape') {
                setIsOpen(false);
            }
        };
        document.addEventListener('keydown', handleKeyDown);
        return () => {
            document.removeEventListener('keydown', handleKeyDown);
        };
    }, [isOpen]);

    useEffect(() => {
        if (isOpen) {
            setShowBell(true);
        }
    }, [isOpen]);

    const fetchFeed = useCallback(async ({ showLoading = true } = {}) => {
        if (!feedUrl || loadingRef.current) {
            return;
        }

        loadingRef.current = true;
        if (showLoading) {
            setLoading(true);
        }
        setErrorMessage('');

        try {
            const response = await apiClient.get(feedUrl, { params: { limit: 20 } });
            const { results, unread_count: unread } = response.data || {};
            setNotifications(Array.isArray(results) ? results : []);
            if (typeof unread === 'number') {
                setUnreadCount(unread);
            }
        } catch (error) {
            console.error('Impossibile recuperare le notifiche', error);
            setErrorMessage('Impossibile caricare le notifiche. Riprova più tardi.');
        } finally {
            loadingRef.current = false;
            setLoading(false);
        }
    }, [feedUrl]);

    useEffect(() => {
        if (!isOpen) {
            return undefined;
        }
        fetchFeed();
        const timer = window.setInterval(() => {
            fetchFeed({ showLoading: false });
        }, FEED_REFRESH_MS);
        return () => {
            window.clearInterval(timer);
        };
    }, [isOpen, fetchFeed]);

    const buildMarkReadUrl = useCallback((notificationId) => {
        if (!markReadTemplate) {
            return null;
        }
        if (markReadTemplate.endsWith('/0/')) {
            return markReadTemplate.replace(/0\/$/, `${notificationId}/`);
        }
        if (markReadTemplate.includes('{id}')) {
            return markReadTemplate.replace('{id}', notificationId);
        }
        return `${markReadTemplate}${notificationId}/`;
    }, [markReadTemplate]);

    const markNotificationAsRead = useCallback(
        async (notificationId, redirectUrl) => {
            const url = buildMarkReadUrl(notificationId);
            if (!url) {
                if (redirectUrl) {
                    window.location.assign(redirectUrl);
                }
                return;
            }

            try {
                const response = await apiClient.post(url);
                const unread = response.data?.unread_count;
                if (typeof unread === 'number') {
                    setUnreadCount(unread);
                }
                if (redirectUrl) {
                    window.location.assign(redirectUrl);
                } else {
                    fetchFeed({ showLoading: false });
                }
            } catch (error) {
                console.error('Impossibile segnare la notifica come letta', error);
                if (redirectUrl) {
                    window.location.assign(redirectUrl);
                }
            }
        },
        [buildMarkReadUrl, fetchFeed],
    );

    const handleInvitationAction = useCallback(
        async (apiUrl, status) => {
            if (!apiUrl) {
                return;
            }
            try {
                await apiClient.post(apiUrl, { status });
                fetchFeed({ showLoading: false });
            } catch (error) {
                console.error("Impossibile aggiornare lo stato dell'invito", error);
            }
        },
        [fetchFeed],
    );

    const handleMarkAll = useCallback(async () => {
        if (!markAllUrl) {
            return;
        }
        try {
            await apiClient.post(markAllUrl);
            await fetchFeed({ showLoading: false });
        } catch (error) {
            console.error('Impossibile segnare tutte le notifiche come lette', error);
        }
    }, [markAllUrl, fetchFeed]);

    const registerForPush = useCallback(async () => {
        if (!pushState.supported) {
            throw new Error('Push non supportate');
        }
        const permission = await Notification.requestPermission();
        if (permission !== 'granted') {
            throw new Error('Permesso negato');
        }

        let registration = swRegistrationRef.current;
        if (!registration) {
            registration = await ensurePwaRegistration();
            swRegistrationRef.current = registration;
        }

        let subscription = await registration.pushManager.getSubscription();
        if (!subscription) {
            if (!webPushPublicKey) {
                throw new Error('Chiave pubblica VAPID non configurata');
            }
            subscription = await registration.pushManager.subscribe({
                userVisibleOnly: true,
                applicationServerKey: urlBase64ToUint8Array(webPushPublicKey),
            });
        }

        const data = subscription.toJSON();
        if (!subscriptionUrl) {
            return;
        }
        await apiClient.post(subscriptionUrl, {
            endpoint: data.endpoint,
            keys: data.keys,
            device_type: getDeviceType(),
        });
    }, [pushState.supported, subscriptionUrl, webPushPublicKey]);

    const handlePush = useCallback(async () => {
        if (!pushState.supported || pushState.status === 'enabled' || pushState.status === 'denied' || pushState.loading) {
            return;
        }
        setPushState((previous) => ({
            ...previous,
            loading: true,
            status: previous.status === 'error' ? 'idle' : previous.status,
        }));
        try {
            await registerForPush();
            setPushState((previous) => ({
                ...previous,
                loading: false,
                status: 'enabled',
                permission: 'granted',
            }));
        } catch (error) {
            console.error('Attivazione push fallita', error);
            setPushState((previous) => ({
                ...previous,
                loading: false,
                status:
                    typeof Notification !== 'undefined' && Notification.permission === 'denied'
                        ? 'denied'
                        : 'error',
                permission: typeof Notification !== 'undefined' ? Notification.permission : previous.permission,
            }));
        }
    }, [pushState.supported, pushState.status, pushState.loading, registerForPush]);

    const closePanel = useCallback(() => {
        setIsOpen(false);
    }, []);

    const panelStyle = useMemo(() => {
        const baseStyle = {
            '--notification-panel-top': `${panelPosition.top}px`,
            '--notification-panel-max-height': `${panelPosition.maxHeight}px`,
            top: `${panelPosition.top}px`,
            maxHeight: `${panelPosition.maxHeight}px`,
            width: `${panelPosition.width}px`,
        };

        if (panelPosition.isMobile) {
            const mobileRight = panelPosition.safeRight + 12;
            baseStyle.left = `${panelPosition.safeLeft + 12}px`;
            baseStyle.right = `${mobileRight}px`;
            baseStyle['--notification-panel-right'] = `${mobileRight}px`;
        } else {
            baseStyle.right = `${panelPosition.right}px`;
            baseStyle['--notification-panel-right'] = `${panelPosition.right}px`;
        }

        return baseStyle;
    }, [panelPosition]);

    const panelClassName = useMemo(() => {
        const classes = ['app-topbar__notifications-panel'];
        classes.push(
            panelPosition.alignment === 'above'
                ? 'app-topbar__notifications-panel--above'
                : 'app-topbar__notifications-panel--below',
        );
        if (panelPosition.isMobile) {
            classes.push('app-topbar__notifications-panel--mobile');
        }
        return classes.join(' ');
    }, [panelPosition]);

    useEffect(() => {
        if (!isOpen || !panelRef.current) {
            return;
        }
        const firstFocusable = panelRef.current.querySelector('button, a');
        firstFocusable?.focus({ preventScroll: true });
    }, [isOpen, notifications]);

    const pushButtonConfig = useMemo(() => {
        if (!pushState.supported) {
            return {
                disabled: true,
                className: 'btn btn-outline-secondary btn-sm me-auto',
                icon: 'fa-ban',
                label: 'Push non supportate',
            };
        }
        if (pushState.status === 'enabled') {
            return {
                disabled: true,
                className: 'btn btn-success btn-sm me-auto',
                icon: 'fa-check',
                label: 'Push attive',
            };
        }
        if (pushState.status === 'denied') {
            return {
                disabled: true,
                className: 'btn btn-outline-danger btn-sm me-auto',
                icon: 'fa-ban',
                label: 'Permesso negato',
            };
        }
        if (pushState.loading) {
            return {
                disabled: true,
                className: 'btn btn-outline-primary btn-sm me-auto',
                spinner: true,
                label: 'Attivazione…',
            };
        }
        if (pushState.status === 'error') {
            return {
                disabled: false,
                className: 'btn btn-outline-danger btn-sm me-auto',
                icon: 'fa-triangle-exclamation',
                label: 'Richiedi permessi',
            };
        }
        return {
            disabled: false,
            className: 'btn btn-outline-primary btn-sm me-auto',
            icon: 'fa-mobile-screen-button',
            label: 'Attiva notifiche push',
        };
    }, [pushState]);

    const overlay = overlayContainerRef.current
        ? createPortal(
              <div className={`notifications-portal__content${isOpen ? ' notifications-portal__content--open' : ''}`}>
                  <button
                      type="button"
                      className="notifications-portal__backdrop"
                      aria-hidden="true"
                      onClick={closePanel}
                      tabIndex={-1}
                  />
                  <section
                      ref={panelRef}
                      className={panelClassName}
                      id={panelId}
                      role="dialog"
                      aria-modal={isOpen ? 'true' : 'false'}
                      aria-label="Centro notifiche"
                      hidden={!isOpen}
                      style={panelStyle}
                  >
                      <div className="notifications-panel__header">
                          <div>
                              <h2 className="notifications-panel__title">Centro notifiche</h2>
                              <p className="notifications-panel__subtitle">Aggiornamenti in tempo reale sul tuo ruolo</p>
                          </div>
                          <button
                              type="button"
                              className="btn btn-link btn-sm notifications-panel__mark-all"
                              onClick={handleMarkAll}
                              disabled={notifications.length === 0 || loading}
                          >
                              <i className="fas fa-check-double me-1" aria-hidden="true" />
                              <span>Segna tutte come lette</span>
                          </button>
                      </div>
                      <div className="notifications-panel__content" role="list">
                          {loading && notifications.length === 0 ? (
                              <div className="notifications-panel__placeholder">
                                  <div className="spinner-border text-primary" role="status" aria-hidden="true" />
                                  <p>Caricamento notifiche…</p>
                              </div>
                          ) : null}
                          {!loading && pushState.supported && pushState.status !== 'enabled' ? (
                              <div className="notifications-panel__onboarding">
                                  <div>
                                      <h3>Ricevi gli avvisi in tempo reale</h3>
                                      <p className="mb-2">
                                          {pushState.status === 'denied'
                                              ? 'Hai disattivato le notifiche per questa applicazione. Per ricevere gli avvisi di manutenzione riattiva il permesso dalle impostazioni del browser.'
                                              : 'Abilita le notifiche push per essere avvisato immediatamente quando un ticket viene assegnato, scade o viene aggiornato.'}
                                      </p>
                                      {pushState.status === 'denied' ? (
                                          <a
                                              className="btn btn-sm btn-outline-primary"
                                              href="https://support.google.com/chrome/answer/3220216?hl=it"
                                              target="_blank"
                                              rel="noreferrer"
                                          >
                                              Guida alle impostazioni
                                          </a>
                                      ) : (
                                          <button
                                              type="button"
                                              className="btn btn-sm btn-primary"
                                              onClick={handlePush}
                                              disabled={pushState.loading}
                                          >
                                              {pushState.loading ? 'Attivazione…' : 'Attiva notifiche push'}
                                          </button>
                                      )}
                                  </div>
                                  <div className="notifications-panel__onboarding-illustration" aria-hidden="true">
                                      <i className="fas fa-bell" />
                                  </div>
                              </div>
                          ) : null}
                          {!loading && errorMessage ? (
                              <div className="notifications-panel__error">{errorMessage}</div>
                          ) : null}
                          {!loading && !errorMessage && notifications.length === 0 ? (
                              <div className="notifications-panel__empty">
                                  <i className="fas fa-bell-slash fa-2x mb-2" aria-hidden="true" />
                                  <p>Nessuna notifica recente.</p>
                              </div>
                          ) : null}
                          {!errorMessage && notifications.length > 0
                              ? notifications.map((notification) => {
                                    const isUnread = notification.type === 'in_app' && notification.is_read === false;
                                    const classes = ['notification-card'];
                                    if (isUnread) {
                                        classes.push('notification-card--unread');
                                    }
                                    if (notification.variant === 'urgent') {
                                        classes.push('notification-card--urgent');
                                    }
                                    if (notification.variant === 'alert') {
                                        classes.push('notification-card--alert');
                                    }
                                    const invitationApi = notification.metadata?.invitation_api;
                                    return (
                                        <article
                                            key={notification.id ?? `${notification.title}-${notification.created_at}`}
                                            className={classes.join(' ')}
                                            role="listitem"
                                        >
                                            <div className="notification-card__icon">
                                                <i className={`fas ${notification.icon || 'fa-bell'}`} aria-hidden="true" />
                                            </div>
                                            <div className="notification-card__content">
                                                <h3 className="notification-card__title">{notification.title || notification.message}</h3>
                                                {notification.body || notification.message ? (
                                                    <p className="notification-card__body">{notification.body || notification.message}</p>
                                                ) : null}
                                                <div className="notification-card__meta">
                                                    {notification.category ? <span>{notification.category}</span> : null}
                                                    {notification.created_at ? (
                                                        <time dateTime={typeof notification.created_at === 'string' ? notification.created_at : ''}>
                                                            {formatDate(notification.created_at)}
                                                        </time>
                                                    ) : null}
                                                </div>
                                                {(notification.type === 'event_invitation' && invitationApi) || notification.cta_url ? (
                                                    <div className="notification-card__actions">
                                                        {notification.type === 'event_invitation' && invitationApi ? (
                                                            <>
                                                                <button
                                                                    type="button"
                                                                    className="btn btn-sm btn-success"
                                                                    onClick={() => handleInvitationAction(invitationApi, 'accepted')}
                                                                >
                                                                    Accetta
                                                                </button>
                                                                <button
                                                                    type="button"
                                                                    className="btn btn-sm btn-outline-secondary"
                                                                    onClick={() => handleInvitationAction(invitationApi, 'declined')}
                                                                >
                                                                    Rifiuta
                                                                </button>
                                                            </>
                                                        ) : null}
                                                        {notification.cta_url ? (
                                                            <a
                                                                href={notification.cta_url}
                                                                className="notification-card__cta"
                                                                onClick={(event) => {
                                                                    if (notification.type === 'in_app' && typeof notification.id === 'number') {
                                                                        event.preventDefault();
                                                                        markNotificationAsRead(notification.id, notification.cta_url);
                                                                    }
                                                                }}
                                                            >
                                                                {notification.cta_label || 'Apri'}
                                                            </a>
                                                        ) : null}
                                                    </div>
                                                ) : null}
                                            </div>
                                        </article>
                                    );
                                })
                              : null}
                      </div>
                      <div className="notifications-panel__footer">
                          <button
                              type="button"
                              className={pushButtonConfig.className}
                              onClick={handlePush}
                              disabled={pushButtonConfig.disabled}
                          >
                              {pushButtonConfig.spinner ? (
                                  <span className="spinner-border spinner-border-sm me-1" aria-hidden="true" />
                              ) : (
                                  <i className={`fas ${pushButtonConfig.icon} me-1`} aria-hidden="true" />
                              )}
                              <span>{pushButtonConfig.label}</span>
                          </button>
                          <button type="button" className="btn btn-outline-secondary btn-sm" onClick={closePanel}>
                              Chiudi
                          </button>
                      </div>
                  </section>
              </div>,
              overlayContainerRef.current,
          )
        : null;

    return (
        <>
            <button
                type="button"
                className="app-topbar__notifications-toggle"
                ref={toggleButtonRef}
                onClick={() => {
                    setShowBell(true);
                    setIsOpen((previous) => !previous);
                }}
                aria-haspopup="true"
                aria-expanded="false"
                aria-controls={panelId}
                title="Apri il centro notifiche"
            >
                <span className="visually-hidden">Apri il centro notifiche</span>
                <i className="fas fa-bell" aria-hidden="true" />
                {badgeValue ? (
                    <span className="app-topbar__notifications-badge">{badgeValue}</span>
                ) : null}
            </button>
            {overlay}
        </>
    );
};

export default NotificationCenter;
