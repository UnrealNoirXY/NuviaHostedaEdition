import { registerSW } from 'virtual:pwa-register';
import { emitPwaEvent } from './events';

let updateServiceWorker;

export const ensurePwaRegistration = () => {
    if (typeof window === 'undefined' || !('serviceWorker' in navigator)) {
        return () => {};
    }

    if (!updateServiceWorker) {
        updateServiceWorker = registerSW({
            immediate: true,
            onNeedRefresh() {
                emitPwaEvent({ type: 'needRefresh' });
            },
            onOfflineReady() {
                emitPwaEvent({ type: 'offlineReady' });
            },
            onRegisteredSW(swUrl, registration) {
                emitPwaEvent({ type: 'registered', swUrl, registration });
            },
            onRegisterError(error) {
                console.error('Registrazione del service worker fallita', error);
                emitPwaEvent({ type: 'error', error });
            },
        });
    }

    return updateServiceWorker;
};

if (typeof window !== 'undefined') {
    ensurePwaRegistration();
}
