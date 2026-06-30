import { addPwaListener } from './events';
import { ensurePwaRegistration } from './registration';

const state = {
    elements: null,
    currentType: null,
    primaryAction: null,
    secondaryAction: null,
    updateServiceWorker: null,
};

const DEFAULT_MAINTENANCE_URL = document.body?.dataset?.maintenanceUrl || '/maintenance/ticket/nuovo/';
const DEFAULT_HUB_URL = document.body?.dataset?.hubUrl || '/';

const TOAST_ICONS = {
    offlineReady: 'fa-circle-check',
    needRefresh: 'fa-rotate',
    error: 'fa-triangle-exclamation',
};

const DEFAULT_QUICK_ACTIONS = {
    offlineReady: [
        {
            label: 'Apri Home',
            href: DEFAULT_HUB_URL,
            icon: 'fa-house',
        },
        {
            label: 'Nuova manutenzione',
            href: DEFAULT_MAINTENANCE_URL,
            icon: 'fa-screwdriver-wrench',
        },
    ],
    needRefresh: [
        {
            label: 'Vedi changelog',
            href: '/changelog/',
            icon: 'fa-bolt',
        },
    ],
    error: [],
};

function formatError(error) {
    if (!error) {
        return 'Si è verificato un errore imprevisto durante la gestione della PWA.';
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
}

function createButton(className) {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = className;
    return button;
}

function buildToastElements() {
    const root = document.createElement('div');
    root.className = 'pwa-toast';
    root.setAttribute('role', 'status');
    root.setAttribute('aria-live', 'polite');
    root.hidden = true;

    const inner = document.createElement('div');
    inner.className = 'pwa-toast-inner';

    const iconWrapper = document.createElement('div');
    iconWrapper.className = 'pwa-toast-icon';
    iconWrapper.setAttribute('aria-hidden', 'true');
    const icon = document.createElement('i');
    icon.className = `fas ${TOAST_ICONS.offlineReady}`;
    iconWrapper.append(icon);

    const body = document.createElement('div');
    body.className = 'pwa-toast-body';
    const title = document.createElement('p');
    title.className = 'pwa-toast-title';
    const message = document.createElement('p');
    message.className = 'pwa-toast-message';
    body.append(title, message);

    const actions = document.createElement('div');
    actions.className = 'pwa-toast-actions';

    const primaryButton = createButton('btn btn-sm btn-primary');
    const primaryIcon = document.createElement('i');
    primaryIcon.className = 'fas fa-rotate me-2';
    const primaryLabel = document.createElement('span');
    primaryLabel.textContent = 'Aggiorna';
    primaryButton.append(primaryIcon, primaryLabel);

    const secondaryButton = createButton('btn btn-sm btn-outline-light');
    const secondaryLabel = document.createElement('span');
    secondaryLabel.textContent = 'Chiudi';
    secondaryButton.append(secondaryLabel);

    actions.append(primaryButton, secondaryButton);

    const quickActions = document.createElement('div');
    quickActions.className = 'pwa-toast-quick-actions';

    inner.append(iconWrapper, body, actions, quickActions);
    root.append(inner);

    return {
        root,
        icon,
        title,
        message,
        actions,
        primaryButton,
        primaryIcon,
        primaryLabel,
        secondaryButton,
        secondaryLabel,
        quickActions,
    };
}

function ensureToastElements() {
    if (!state.elements) {
        state.elements = buildToastElements();
        document.body.appendChild(state.elements.root);
        state.elements.primaryButton.addEventListener('click', onPrimaryAction);
        state.elements.secondaryButton.addEventListener('click', onSecondaryAction);
    } else if (!state.elements.root.isConnected) {
        document.body.appendChild(state.elements.root);
    }

    return state.elements;
}

function hideToast() {
    if (!state.elements) {
        return;
    }

    state.elements.root.hidden = true;
    state.elements.root.classList.remove('is-visible');
    state.currentType = null;
    state.primaryAction = null;
    state.secondaryAction = null;
    if (state.elements.quickActions) {
        state.elements.quickActions.innerHTML = '';
    }
}

function onPrimaryAction(event) {
    event.preventDefault();
    if (typeof state.primaryAction === 'function') {
        state.primaryAction();
    }
}

function onSecondaryAction(event) {
    event.preventDefault();
    if (typeof state.secondaryAction === 'function') {
        state.secondaryAction();
    } else {
        hideToast();
    }
}

function configureActions(type, messageText) {
    const {
        primaryButton,
        primaryIcon,
        primaryLabel,
        secondaryButton,
        secondaryLabel,
    } = ensureToastElements();

    state.secondaryAction = hideToast;

    switch (type) {
        case 'needRefresh': {
            primaryButton.hidden = false;
            primaryButton.disabled = false;
            primaryIcon.className = 'fas fa-rotate me-2';
            primaryLabel.textContent = 'Aggiorna';
            state.primaryAction = () => {
                hideToast();
                state.updateServiceWorker?.(true);
            };

            secondaryButton.hidden = false;
            secondaryLabel.textContent = 'Più tardi';
            break;
        }
        case 'error': {
            primaryButton.hidden = false;
            primaryButton.disabled = false;
            primaryIcon.className = 'fas fa-sync me-2';
            primaryLabel.textContent = 'Riprova';
            state.primaryAction = () => {
                hideToast();
                state.updateServiceWorker = ensurePwaRegistration();
            };

            secondaryButton.hidden = false;
            secondaryLabel.textContent = 'Chiudi';
            break;
        }
        case 'offlineReady':
        default: {
            primaryButton.hidden = true;
            state.primaryAction = null;

            secondaryButton.hidden = false;
            secondaryLabel.textContent = messageText ? 'Ho capito' : 'Chiudi';
            break;
        }
    }
}

function renderToastQuickActions(actions = []) {
    const { quickActions } = ensureToastElements();
    quickActions.innerHTML = '';

    if (!actions.length) {
        quickActions.hidden = true;
        return;
    }

    quickActions.hidden = false;

    actions.slice(0, 3).forEach((action) => {
        const button = createButton('btn btn-sm btn-outline-light pwa-toast-quick');
        const icon = document.createElement('i');
        icon.className = `fas ${action.icon || 'fa-arrow-up-right-from-square'} me-2`;
        const label = document.createElement('span');
        label.textContent = action.label;
        button.append(icon, label);

        if (typeof action.onClick === 'function') {
            button.addEventListener('click', (event) => {
                event.preventDefault();
                hideToast();
                action.onClick();
            });
        } else if (action.href) {
            button.addEventListener('click', (event) => {
                event.preventDefault();
                hideToast();
                window.location.assign(action.href);
            });
        }

        quickActions.append(button);
    });
}

function showToast(type, messageText, options = {}) {
    const { root, icon, title, message } = ensureToastElements();

    state.currentType = type;

    const iconClass = TOAST_ICONS[type] || TOAST_ICONS.offlineReady;
    icon.className = `fas ${iconClass}`;

    switch (type) {
        case 'needRefresh':
            title.textContent = 'Aggiornamento disponibile';
            message.textContent = messageText || 'Ricarica per applicare le ultime ottimizzazioni della piattaforma.';
            break;
        case 'error':
            title.textContent = 'Errore PWA';
            message.textContent = messageText || 'Non è stato possibile completare l\'operazione richiesta.';
            break;
        case 'offlineReady':
        default:
            title.textContent = 'Pronto all\'uso offline';
            message.textContent = messageText || 'Puoi continuare a utilizzare la piattaforma anche senza connessione.';
            break;
    }

    configureActions(type, messageText);
    const quickActions = options.actions && options.actions.length
        ? options.actions
        : DEFAULT_QUICK_ACTIONS[type] || [];
    renderToastQuickActions(quickActions);

    root.hidden = false;
    requestAnimationFrame(() => {
        root.classList.add('is-visible');
    });
}

function handlePwaEvent(event) {
    switch (event.type) {
        case 'offlineReady':
            showToast('offlineReady', event.message, { actions: event.actions });
            break;
        case 'needRefresh':
            showToast('needRefresh', event.message, { actions: event.actions });
            break;
        case 'error':
            showToast('error', formatError(event.error), { actions: event.actions });
            break;
        default:
            break;
    }
}

function bootstrapStatusToast() {
    if (typeof window === 'undefined' || typeof document === 'undefined') {
        return;
    }

    state.updateServiceWorker = ensurePwaRegistration();
    addPwaListener(handlePwaEvent);
}

bootstrapStatusToast();
