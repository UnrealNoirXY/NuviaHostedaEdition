import { useEffect, useRef, useState } from 'react';
import { addPwaListener } from '../pwa/events';
import { ensurePwaRegistration } from '../pwa/registration';

const formatError = (error) => {
    if (!error) {
        return null;
    }

    if (typeof error === 'string') {
        return error;
    }

    if (error?.message) {
        return error.message;
    }

    try {
        return JSON.stringify(error);
    } catch (serializationError) {
        console.error('Impossibile serializzare l\'errore PWA', serializationError);
        return 'Errore sconosciuto durante la registrazione della PWA';
    }
};

const usePwaRegistration = () => {
    const [offlineReady, setOfflineReady] = useState(false);
    const [needsRefresh, setNeedsRefresh] = useState(false);
    const [registration, setRegistration] = useState(null);
    const [error, setError] = useState(null);
    const updateServiceWorkerRef = useRef(null);

    useEffect(() => {
        updateServiceWorkerRef.current = ensurePwaRegistration();

        const unsubscribe = addPwaListener((event) => {
            switch (event.type) {
                case 'offlineReady':
                    setOfflineReady(true);
                    break;
                case 'needRefresh':
                    setNeedsRefresh(true);
                    break;
                case 'registered':
                    setRegistration(event.registration || null);
                    break;
                case 'error':
                    setError(formatError(event.error));
                    break;
                default:
                    break;
            }
        });

        return () => {
            unsubscribe();
        };
    }, []);

    useEffect(() => {
        let cancelled = false;

        const detectExistingRegistration = async () => {
            if (typeof window === 'undefined' || !('serviceWorker' in navigator)) {
                return;
            }

            try {
                const readyRegistration = await navigator.serviceWorker.ready;

                if (cancelled) {
                    return;
                }

                if (readyRegistration) {
                    setRegistration((prev) => prev || readyRegistration);
                    setOfflineReady((prev) => prev || Boolean(readyRegistration.active));
                }
            } catch (readyError) {
                if (!cancelled) {
                    setError(formatError(readyError));
                }
            }
        };

        detectExistingRegistration();

        return () => {
            cancelled = true;
        };
    }, []);

    const refreshApp = () => {
        if (updateServiceWorkerRef.current) {
            updateServiceWorkerRef.current(true);
        }
    };

    const dismissNotification = () => {
        setOfflineReady(false);
        setNeedsRefresh(false);
        setError(null);
    };

    return {
        offlineReady,
        needsRefresh,
        registration,
        error,
        refreshApp,
        dismissNotification,
    };
};

export default usePwaRegistration;
