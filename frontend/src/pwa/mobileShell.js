import { collectSidebarMenuItems, SIDEBAR_CONTAINER_SELECTOR } from '../utils/sidebarMenu';
import { fetchMobileShellContext } from './api/mobileShellApi';

const MOBILE_MEDIA_QUERY = '(max-width: 767px)';
const BODY_ACTIVE_CLASS = 'has-mobile-command';
const BODY_MENU_OPEN_CLASS = 'mobile-menu-open';
const BODY_HIGH_CONTRAST_CLASS = 'mobile-high-contrast';

const DEFAULT_LOGO_SRC = '/static/img/logo.png';
const DEFAULT_AVATAR_SRC = DEFAULT_LOGO_SRC;
const DEFAULT_HUB_URL = '/';
const DEFAULT_MAINTENANCE_URL = '/maintenance/ticket/nuovo/';
const DEFAULT_PROFILE_URL = '/profilo/';
const DEFAULT_LOGOUT_URL = '/logout/';
const DEFAULT_PROFILE_NAME = 'Utente';
const DEFAULT_VOICE_ENDPOINT = '/api/voice-search';

const QUICK_ACTIONS_KEY = 'mobileShell.quickActions';
const RECENTS_KEY = 'mobileShell.recents';
const HIGH_CONTRAST_KEY = 'mobileShell.highContrast';
const MAX_RECENTS = 6;
const MAX_QUICK_ACTIONS = 4;

const HUB_LABEL_PATTERN = /hub/i;
const DESK_LABEL_PATTERN = /home\s*desk/i;

const SPEECH_RECOGNITION_KEY =
    typeof window !== 'undefined'
        ? window.SpeechRecognition || window.webkitSpeechRecognition || null
        : null;
const ALLOWED_RECORDING_MIME_TYPES = [
    'audio/webm;codecs=opus',
    'audio/mp4',
    'audio/ogg;codecs=opus',
    'audio/webm',
];
const MAX_RECORDING_DURATION_MS = 30000;
const VOICE_UPLOAD_TIMEOUT_MS = 15000;

const state = {
    elements: null,
    menuItems: [],
    homeLink: null,
    sidebarObserver: null,
    mediaQuery: null,
    sheetOpen: false,
    isActive: false,
    previousOverflow: null,
    quickActions: [],
    recentItems: [],
    searchTerm: '',
    editQuickActions: false,
    speechRecognizer: null,
    mediaRecorder: null,
    recordingStream: null,
    recordingChunks: [],
    isRecording: false,
    isProcessingVoice: false,
    context: null,
    contextPromise: null,
    recordingTimeoutId: null,
    voiceError: '',
};

async function ensureContextLoaded() {
    if (state.context) {
        return state.context;
    }

    if (!state.contextPromise) {
        state.contextPromise = fetchMobileShellContext()
            .then((payload) => {
                state.context = payload;
                state.menuItems = payload.navigation || [];
                if (!state.quickActions.length && Array.isArray(payload.quickActionsDefaults)) {
                    state.quickActions = payload.quickActionsDefaults.slice(0, MAX_QUICK_ACTIONS);
                    saveQuickActions(state.quickActions);
                }
                return payload;
            })
            .catch((error) => {
                console.warn('Impossibile caricare il contesto mobile shell', error);
                state.context = null;
                return null;
            })
            .finally(() => {
                state.contextPromise = null;
            });
    }

    return state.contextPromise;
}

function isInternalUrl(url) {
    if (!url) {
        return false;
    }
    if (url.startsWith('http://') || url.startsWith('https://')) {
        try {
            const target = new URL(url, window.location.origin);
            return target.origin === window.location.origin;
        } catch (error) {
            return false;
        }
    }
    return true;
}

function normalizePath(url) {
    try {
        const target = url.startsWith('http') ? new URL(url) : new URL(url, window.location.origin);
        return target.pathname.replace(/\/+$/, '') || '/';
    } catch (error) {
        return url;
    }
}

async function navigateClientSide(url, { replace = false } = {}) {
    if (!url) {
        return;
    }

    if (typeof window === 'undefined') {
        return;
    }

    if (!isInternalUrl(url)) {
        window.location.assign(url);
        return;
    }

    const absoluteUrl = url.startsWith('http') ? url : new URL(url, window.location.origin).toString();

    try {
        const response = await fetch(absoluteUrl, {
            credentials: 'same-origin',
            headers: {
                'X-Mobile-Navigation': '1',
                'X-Requested-With': 'XMLHttpRequest',
                Accept: 'text/html,application/xhtml+xml',
            },
        });

        if (!response.ok) {
            throw new Error(`Risposta non valida (${response.status})`);
        }

        const html = await response.text();
        const parser = new DOMParser();
        const doc = parser.parseFromString(html, 'text/html');
        const nextContent = doc.querySelector('.app-content');

        if (!nextContent) {
            throw new Error('Contenuto principale non trovato');
        }

        const currentContent = document.querySelector('.app-content');
        if (currentContent) {
            currentContent.replaceWith(nextContent);
        } else {
            document.body.appendChild(nextContent);
        }

        if (doc.title) {
            document.title = doc.title;
        }

        if (replace) {
            window.history.replaceState({}, '', absoluteUrl);
        } else {
            window.history.pushState({}, '', absoluteUrl);
        }

        refreshMenuItems(Boolean(!state.context));
        window.dispatchEvent(new CustomEvent('mobileShell:navigation', { detail: { url: absoluteUrl } }));
    } catch (error) {
        console.warn('Navigazione client non riuscita, fallback a ricaricamento completo', error);
        window.location.assign(url);
    }
}

function createElement(tag, className, attributes = {}) {
    const element = document.createElement(tag);
    if (className) {
        element.className = className;
    }
    Object.entries(attributes).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
            element.setAttribute(key, value);
        }
    });
    return element;
}

function getContext() {
    return state.context || {};
}

function getShortcut(key, fallback) {
    return getContext().shortcuts?.[key] || fallback;
}

function getAvatarUrl() {
    return getContext().user?.avatarUrl || document.body?.dataset?.avatarUrl || DEFAULT_AVATAR_SRC;
}

function getProfileAvatarUrl() {
    return getAvatarUrl();
}

function getHubUrl() {
    return getShortcut('hub', document.body?.dataset?.hubUrl || DEFAULT_HUB_URL);
}

function getMaintenanceUrl() {
    return getShortcut('maintenance', document.body?.dataset?.maintenanceUrl || DEFAULT_MAINTENANCE_URL);
}

function getProfileName() {
    return getContext().user?.fullName || document.body?.dataset?.userName || DEFAULT_PROFILE_NAME;
}

function getProfileUrl() {
    return getShortcut('profile', document.body?.dataset?.profileUrl || DEFAULT_PROFILE_URL);
}

function getLogoutUrl() {
    return getShortcut('logout', document.body?.dataset?.logoutUrl || DEFAULT_LOGOUT_URL);
}

function getVoiceSearchEndpoint() {
    return getShortcut('voiceSearch', DEFAULT_VOICE_ENDPOINT);
}

function safeJsonParse(value, fallback) {
    if (!value) {
        return fallback;
    }

    try {
        return JSON.parse(value);
    } catch (error) {
        console.warn('Impossibile analizzare la preferenza salvata', error);
        return fallback;
    }
}

function loadPreference(key, fallback) {
    if (typeof window === 'undefined') {
        return fallback;
    }

    try {
        const stored = window.localStorage.getItem(key);
        return safeJsonParse(stored, fallback);
    } catch (error) {
        console.warn('Impossibile leggere le preferenze mobile shell', error);
        return fallback;
    }
}

function savePreference(key, value) {
    if (typeof window === 'undefined') {
        return;
    }

    try {
        window.localStorage.setItem(key, JSON.stringify(value));
    } catch (error) {
        console.warn('Impossibile salvare le preferenze mobile shell', error);
    }
}

function loadQuickActions() {
    return loadPreference(QUICK_ACTIONS_KEY, []);
}

function saveQuickActions(next) {
    savePreference(QUICK_ACTIONS_KEY, next);
}

function loadRecents() {
    return loadPreference(RECENTS_KEY, []);
}

function saveRecents(next) {
    savePreference(RECENTS_KEY, next);
}

function loadHighContrastPreference() {
    return Boolean(loadPreference(HIGH_CONTRAST_KEY, false));
}

function saveHighContrastPreference(value) {
    savePreference(HIGH_CONTRAST_KEY, Boolean(value));
}

function highlightMatches(labelElement, text, query) {
    labelElement.textContent = '';

    if (!query) {
        labelElement.textContent = text;
        return;
    }

    const normalizedText = text.toLocaleLowerCase('it-IT');
    const normalizedQuery = query.toLocaleLowerCase('it-IT');
    let startIndex = 0;
    let matchIndex = normalizedText.indexOf(normalizedQuery);

    if (matchIndex === -1) {
        labelElement.textContent = text;
        return;
    }

    while (matchIndex !== -1) {
        if (matchIndex > startIndex) {
            labelElement.append(text.slice(startIndex, matchIndex));
        }
        const mark = document.createElement('mark');
        mark.textContent = text.slice(matchIndex, matchIndex + normalizedQuery.length);
        labelElement.append(mark);
        startIndex = matchIndex + normalizedQuery.length;
        matchIndex = normalizedText.indexOf(normalizedQuery, startIndex);
    }

    if (startIndex < text.length) {
        labelElement.append(text.slice(startIndex));
    }
}

function computeSearchScore(item, query) {
    const label = item.label?.toLocaleLowerCase('it-IT') || '';
    const normalizedQuery = query.toLocaleLowerCase('it-IT');
    const position = label.indexOf(normalizedQuery);

    if (position === -1) {
        return null;
    }

    const depthWeight = (item.depth || 0) * 2;
    const activeBoost = item.isActive ? -4 : 0;
    return position + depthWeight + activeBoost;
}

function trackMenuUsage(item) {
    if (!item || !item.href) {
        return;
    }

    const nextRecents = [
        {
            href: item.href,
            label: item.label,
            iconClass: item.iconClass,
            lastUsedAt: Date.now(),
        },
        ...state.recentItems.filter((recent) => recent.href !== item.href),
    ].slice(0, MAX_RECENTS);

    state.recentItems = nextRecents;
    saveRecents(nextRecents);
}

function createSectionHeader(title) {
    const header = createElement('div', 'mobile-menu-section-header');
    const label = createElement('span', 'mobile-menu-section-title');
    label.textContent = title;
    header.append(label);
    return header;
}

function buildShellElements() {
    const quickTray = createElement('div', 'mobile-quick-actions');
    const quickTrayScroll = createElement('div', 'mobile-quick-actions-scroll');
    quickTray.append(quickTrayScroll);

    const commandBar = createElement('nav', 'desk-mobile-command', {
        'aria-label': 'Navigazione principale mobile',
    });

    const leftSlot = createElement('div', 'command-slot');
    const rightSlot = createElement('div', 'command-slot');

    const homeButton = createElement('button', 'command-button', { type: 'button' });
    const homeIcon = createElement('i', 'fas fa-house', { 'aria-hidden': 'true' });
    const homeLabel = createElement('span');
    homeLabel.textContent = 'Home';
    homeButton.append(homeIcon, homeLabel);
    leftSlot.append(homeButton);

    const commandCenter = createElement('div', 'command-center');
    const fabButton = createElement('button', 'command-fab', {
        type: 'button',
        'aria-label': 'Apri richiesta di manutenzione',
    });
    const fabAvatar = createElement('img', 'command-fab-avatar', {
        src: getAvatarUrl(),
        alt: 'Profilo utente',
        decoding: 'async',
        loading: 'lazy',
    });
    fabButton.append(fabAvatar);
    const fabLabel = createElement('span', 'command-fab-label');
    fabLabel.textContent = 'Richiesta manutenzione';
    commandCenter.append(fabButton, fabLabel);

    const menuButton = createElement('button', 'command-button', {
        type: 'button',
        'aria-haspopup': 'dialog',
        'aria-expanded': 'false',
        'aria-controls': 'mobile-menu-sheet',
    });
    const menuIcon = createElement('i', 'fas fa-bars', { 'aria-hidden': 'true' });
    const menuLabel = createElement('span');
    menuLabel.textContent = 'Menu';
    menuButton.append(menuIcon, menuLabel);
    rightSlot.append(menuButton);

    commandBar.append(leftSlot, commandCenter, rightSlot);

    const overlay = createElement('div', 'mobile-menu-overlay', {
        role: 'dialog',
        'aria-modal': 'true',
        'aria-label': 'Navigazione rapida',
    });
    overlay.hidden = true;

    const backdrop = createElement('button', 'mobile-menu-backdrop', { type: 'button' });
    const sheet = createElement('div', 'mobile-menu-sheet', {
        id: 'mobile-menu-sheet',
        tabindex: '-1',
    });

    const header = createElement('div', 'mobile-menu-header');
    const handle = createElement('div', 'mobile-menu-handle', { 'aria-hidden': 'true' });
    const titleBar = createElement('div', 'mobile-menu-title');
    const titleText = createElement('span');
    titleText.textContent = 'Menu principale';
    const headerActions = createElement('div', 'mobile-menu-actions');
    const quickEditButton = createElement('button', 'mobile-menu-quick-edit', {
        type: 'button',
    });
    quickEditButton.textContent = 'Personalizza azioni rapide';
    const closeButton = createElement('button', 'mobile-menu-close', {
        type: 'button',
        'aria-label': 'Chiudi menu',
    });
    const closeIcon = createElement('i', 'fas fa-xmark', { 'aria-hidden': 'true' });
    closeButton.append(closeIcon);
    headerActions.append(quickEditButton, closeButton);
    titleBar.append(titleText, headerActions);
    header.append(handle, titleBar);

    const searchContainer = createElement('div', 'mobile-menu-search');
    const searchIcon = createElement('i', 'fas fa-magnifying-glass', { 'aria-hidden': 'true' });
    const searchInput = createElement('input', 'mobile-menu-search-input', {
        type: 'search',
        placeholder: 'Cerca funzioni, clienti, ticket…',
        autocapitalize: 'none',
        autocomplete: 'off',
    });
    const searchButtons = createElement('div', 'mobile-menu-search-actions');
    const clearButton = createElement('button', 'mobile-menu-search-clear', {
        type: 'button',
        'aria-label': 'Cancella ricerca',
    });
    clearButton.append(createElement('i', 'fas fa-circle-xmark', { 'aria-hidden': 'true' }));

    const micButton = createElement('button', 'mobile-menu-search-mic', {
        type: 'button',
        'aria-label': 'Ricerca vocale',
        disabled: SPEECH_RECOGNITION_KEY ? null : 'disabled',
    });
    micButton.append(createElement('i', 'fas fa-microphone', { 'aria-hidden': 'true' }));
    const micStatus = createElement('p', 'mobile-menu-mic-status visually-hidden', {
        'aria-live': 'polite',
        role: 'status',
    });
    micStatus.textContent = 'Ricerca vocale pronta.';

    searchButtons.append(clearButton, micButton);
    searchContainer.append(searchIcon, searchInput, searchButtons, micStatus);

    const sections = createElement('div', 'mobile-menu-sections');

    const quickActionsSection = createElement('section', 'mobile-menu-section mobile-menu-section-quick');
    quickActionsSection.append(createSectionHeader('Azioni rapide personalizzate'));
    const quickActionsBody = createElement('div', 'mobile-quick-actions-editor');
    const quickActionsHint = createElement('p', 'mobile-quick-actions-hint');
    quickActionsHint.textContent = 'Trascina con le frecce per riordinare o aggiungi scorciatoie dalle voci disponibili.';
    const quickActionsSelected = createElement('div', 'mobile-quick-actions-selected');
    const quickActionsAvailable = createElement('div', 'mobile-quick-actions-available');
    quickActionsBody.append(quickActionsHint, quickActionsSelected, quickActionsAvailable);
    quickActionsSection.append(quickActionsBody);

    const recentSection = createElement('section', 'mobile-menu-section mobile-menu-section-recents');
    recentSection.append(createSectionHeader('Usati di recente'));
    const recentList = createElement('ul', 'mobile-menu-list mobile-recent-list');
    recentSection.append(recentList);

    const navigationSection = createElement('section', 'mobile-menu-section mobile-menu-section-navigation');
    const navigationHeader = createSectionHeader('Navigazione completa');
    navigationSection.append(navigationHeader);
    const menuList = createElement('ul', 'mobile-menu-list');
    const emptyState = createElement('p', 'mobile-menu-empty');
    emptyState.textContent = 'Nessuna voce corrisponde alla tua ricerca.';
    navigationSection.append(menuList, emptyState);

    const settingsSection = createElement('section', 'mobile-menu-section mobile-menu-section-settings');
    settingsSection.append(createSectionHeader('Preferenze rapide'));
    const settingsList = createElement('div', 'mobile-menu-settings');
    const highContrastLabel = createElement('label', 'mobile-settings-toggle');
    const highContrastToggle = createElement('input', null, {
        type: 'checkbox',
        role: 'switch',
    });
    const highContrastCopy = createElement('span');
    highContrastCopy.textContent = 'Tema ad alto contrasto';
    highContrastLabel.append(highContrastToggle, highContrastCopy);
    settingsList.append(highContrastLabel);
    settingsSection.append(settingsList);

    sections.append(
        quickActionsSection,
        recentSection,
        navigationSection,
        settingsSection,
    );

    const profileCard = createElement('section', 'mobile-menu-profile');
    const profileAvatarButton = createElement('button', 'mobile-profile-avatar', {
        type: 'button',
        'aria-label': 'Apri il profilo utente',
    });
    const profileAvatarImage = createElement('img', null, {
        src: getProfileAvatarUrl(),
        alt: getProfileName(),
        loading: 'lazy',
    });
    profileAvatarButton.append(profileAvatarImage);

    const profileSummary = createElement('div', 'mobile-profile-summary');
    const profileNameLabel = createElement('p', 'mobile-profile-name');
    profileNameLabel.textContent = getProfileName();
    const profileActionBar = createElement('div', 'mobile-profile-actions');
    const openProfileButton = createElement('button', 'mobile-profile-link', {
        type: 'button',
    });
    openProfileButton.textContent = 'Profilo';
    const logoutButton = createElement('button', 'mobile-profile-link mobile-profile-logout', {
        type: 'button',
    });
    logoutButton.textContent = 'Logout';

    profileActionBar.append(openProfileButton, logoutButton);
    profileSummary.append(profileNameLabel, profileActionBar);
    profileCard.append(profileAvatarButton, profileSummary);

    const content = createElement('div', 'mobile-menu-content');
    content.append(profileCard, searchContainer, sections);

    sheet.append(header, content);
    overlay.append(backdrop, sheet);

    return {
        quickTray,
        quickTrayScroll,
        commandBar,
        leftSlot,
        rightSlot,
        homeButton,
        homeLabel,
        menuButton,
        fabButton,
        fabAvatar,
        overlay,
        backdrop,
        closeButton,
        sheet,
        quickEditButton,
        searchInput,
        clearButton,
        micButton,
        micStatus,
        quickActionsSection,
        quickActionsSelected,
        quickActionsAvailable,
        quickActionsHint,
        recentSection,
        recentList,
        menuList,
        emptyState,
        navigationSection,
        searchContainer,
        highContrastToggle,
        profileCard,
        profileAvatarButton,
        profileAvatarImage,
        profileNameLabel,
        openProfileButton,
        logoutButton,
    };
}

function ensureElements() {
    if (!state.elements) {
        state.elements = buildShellElements();
        const {
            overlay,
            backdrop,
            closeButton,
            quickEditButton,
            searchInput,
            clearButton,
            micButton,
            micStatus,
            highContrastToggle,
            profileAvatarButton,
            openProfileButton,
            logoutButton,
        } = state.elements;

        overlay.addEventListener('click', handleOverlayClick);
        backdrop.addEventListener('click', closeMenuSheet);
        closeButton.addEventListener('click', closeMenuSheet);
        quickEditButton.addEventListener('click', toggleQuickActionsEditMode);
        searchInput.addEventListener('input', handleSearchInput);
        clearButton.addEventListener('click', clearSearch);
        micButton.addEventListener('click', handleVoiceSearch);
        highContrastToggle.addEventListener('change', handleHighContrastToggle);
        profileAvatarButton.addEventListener('click', navigateToProfile);
        openProfileButton.addEventListener('click', navigateToProfile);
        logoutButton.addEventListener('click', handleLogout);
    }
    updateVoiceControlUi();
    renderProfileCard();
    return state.elements;
}

function handleVoiceSearch() {
    if (state.isProcessingVoice) {
        return;
    }

    if (supportsServerVoiceSearch()) {
        if (state.isRecording) {
            stopServerVoiceRecording();
        } else {
            startServerVoiceRecording();
        }
        return;
    }

    if (!SPEECH_RECOGNITION_KEY) {
        return;
    }

    if (!state.speechRecognizer) {
        state.speechRecognizer = new SPEECH_RECOGNITION_KEY();
        state.speechRecognizer.lang = 'it-IT';
        state.speechRecognizer.interimResults = false;
        state.speechRecognizer.maxAlternatives = 1;
        state.speechRecognizer.addEventListener('result', (event) => {
            const transcript = event.results?.[0]?.[0]?.transcript;
            if (transcript) {
                const { searchInput } = ensureElements();
                searchInput.value = transcript;
                state.searchTerm = transcript;
                renderMenuOverlay();
            }
        });
    }

    try {
        state.speechRecognizer.start();
    } catch (error) {
        console.warn('Impossibile avviare la ricerca vocale', error);
    }
}

function supportsServerVoiceSearch() {
    if (typeof navigator === 'undefined' || typeof window === 'undefined') {
        return false;
    }
    return Boolean(navigator.mediaDevices?.getUserMedia && window.MediaRecorder);
}

function isAllowedMimeType(mimeType) {
    if (!mimeType) {
        return false;
    }
    return ALLOWED_RECORDING_MIME_TYPES.some((allowed) => mimeType.toLowerCase().startsWith(allowed));
}

function resolvePreferredMimeType() {
    if (typeof window === 'undefined' || !window.MediaRecorder) {
        return null;
    }

    for (const type of ALLOWED_RECORDING_MIME_TYPES) {
        if (window.MediaRecorder.isTypeSupported?.(type)) {
            return type;
        }
    }

    return null;
}

function getUploadMimeType(recorderMimeType) {
    if (recorderMimeType && isAllowedMimeType(recorderMimeType)) {
        return recorderMimeType;
    }
    const preferred = resolvePreferredMimeType();
    if (preferred) {
        return preferred;
    }
    const fallback = ALLOWED_RECORDING_MIME_TYPES.find((type) => isAllowedMimeType(type));
    return fallback || 'audio/webm';
}

function clearRecordingTimeout() {
    if (state.recordingTimeoutId) {
        clearTimeout(state.recordingTimeoutId);
        state.recordingTimeoutId = null;
    }
}

function setVoiceError(message) {
    state.voiceError = message || '';
    updateVoiceControlUi();
}

async function startServerVoiceRecording() {
    if (!supportsServerVoiceSearch() || state.isRecording || state.isProcessingVoice) {
        return;
    }

    try {
        setVoiceError('');
        const stream = await navigator.mediaDevices.getUserMedia({
            audio: {
                echoCancellation: true,
                noiseSuppression: true,
                channelCount: 1,
            },
        });

        state.recordingChunks = [];
        const options = {};
        const mimeType = resolvePreferredMimeType();
        if (mimeType) {
            options.mimeType = mimeType;
        }

        const recorder = new MediaRecorder(stream, options);
        recorder.addEventListener('dataavailable', (event) => {
            if (event?.data && event.data.size > 0) {
                state.recordingChunks.push(event.data);
            }
        });
        recorder.addEventListener('stop', () => {
            handleVoiceRecordingStop(recorder);
        });

        state.recordingStream = stream;
        state.mediaRecorder = recorder;
        state.isRecording = true;
        updateVoiceControlUi();
        recorder.start();
        clearRecordingTimeout();
        state.recordingTimeoutId = setTimeout(() => {
            if (state.mediaRecorder && state.mediaRecorder.state === 'recording') {
                state.isRecording = false;
                state.isProcessingVoice = true;
                state.mediaRecorder.stop();
                updateVoiceControlUi();
            }
        }, MAX_RECORDING_DURATION_MS);
    } catch (error) {
        console.warn('Impossibile avviare la registrazione vocale', error);
        setVoiceError('Non è stato possibile accedere al microfono.');
        teardownVoiceRecorder();
    }
}

function stopServerVoiceRecording() {
    if (!state.mediaRecorder) {
        return;
    }

    if (state.mediaRecorder.state === 'inactive') {
        return;
    }

    state.isRecording = false;
    state.isProcessingVoice = true;
    updateVoiceControlUi();
    clearRecordingTimeout();
    state.mediaRecorder.stop();
}

function handleVoiceRecordingStop(recorder) {
    clearRecordingTimeout();
    const fallbackType = getUploadMimeType(recorder?.mimeType);
    let blob = state.recordingChunks.length
        ? new Blob(state.recordingChunks, { type: recorder?.mimeType || fallbackType })
        : null;

    if (state.recordingStream) {
        state.recordingStream.getTracks().forEach((track) => track.stop());
    }

    state.mediaRecorder = null;
    state.recordingStream = null;
    state.recordingChunks = [];

    if (!blob) {
        state.isProcessingVoice = false;
        updateVoiceControlUi();
        return;
    }

    if (!isAllowedMimeType(blob.type)) {
        blob = new Blob(state.recordingChunks, { type: fallbackType });
    }

    if (!isAllowedMimeType(blob.type)) {
        setVoiceError('Formato audio non supportato per la ricerca vocale.');
        state.isProcessingVoice = false;
        updateVoiceControlUi();
        return;
    }

    uploadVoiceSearch(blob)
        .catch((error) => {
            console.warn('Impossibile completare la trascrizione vocale', error);
            setVoiceError('Errore durante la trascrizione della registrazione.');
        })
        .finally(() => {
            state.isProcessingVoice = false;
            updateVoiceControlUi();
        });
}

function teardownVoiceRecorder() {
    if (state.mediaRecorder && state.mediaRecorder.state !== 'inactive') {
        try {
            state.mediaRecorder.stop();
        } catch (error) {
            console.warn('Errore fermando la registrazione vocale', error);
        }
    }

    clearRecordingTimeout();

    if (state.recordingStream) {
        state.recordingStream.getTracks().forEach((track) => track.stop());
    }

    state.mediaRecorder = null;
    state.recordingStream = null;
    state.recordingChunks = [];
    state.isRecording = false;
    state.isProcessingVoice = false;
    updateVoiceControlUi();
}

async function uploadVoiceSearch(blob) {
    const endpoint = getVoiceSearchEndpoint();
    const formData = new FormData();
    const extension = blob.type.includes('mp4') ? 'mp4' : blob.type.includes('ogg') ? 'ogg' : 'webm';
    formData.append('file', blob, `ricerca-vocale.${extension}`);
    formData.append('language', 'it');

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), VOICE_UPLOAD_TIMEOUT_MS);

    let response;
    try {
        response = await fetch(endpoint, {
            method: 'POST',
            body: formData,
            credentials: 'include',
            signal: controller.signal,
        });
    } catch (error) {
        setVoiceError(error?.name === 'AbortError' ? 'Timeout durante il caricamento audio.' : 'Errore di rete nella ricerca vocale.');
        throw error;
    } finally {
        clearTimeout(timeoutId);
    }

    if (!response.ok) {
        setVoiceError(`Trascrizione non riuscita (status ${response.status}).`);
        throw new Error(`Voice transcription failed with status ${response.status}`);
    }

    const payload = await response.json();
    const transcript = payload?.query || payload?.text || '';
    if (!transcript) {
        setVoiceError('Nessun testo riconosciuto dalla registrazione.');
        return;
    }

    const { searchInput } = ensureElements();
    searchInput.value = transcript;
    state.searchTerm = transcript;
    renderMenuOverlay();
}

function updateVoiceControlUi() {
    const micButton = state.elements?.micButton;
    const micStatus = state.elements?.micStatus;
    if (!micButton) {
        return;
    }

    const supportsRecording = supportsServerVoiceSearch();
    const canFallback = Boolean(SPEECH_RECOGNITION_KEY);
    const isBusy = state.isProcessingVoice;
    micButton.disabled = (!supportsRecording && !canFallback) || isBusy;
    micButton.classList.toggle('is-recording', state.isRecording);
    micButton.classList.toggle('is-processing', isBusy);
    micButton.classList.toggle('is-error', Boolean(state.voiceError));
    micButton.dataset.state = state.isRecording
        ? 'recording'
        : state.isProcessingVoice
            ? 'processing'
            : state.voiceError
                ? 'error'
                : 'idle';
    micButton.setAttribute('aria-pressed', state.isRecording ? 'true' : 'false');

    if (isBusy) {
        micButton.setAttribute('aria-busy', 'true');
    } else {
        micButton.removeAttribute('aria-busy');
    }

    if (state.isRecording) {
        micButton.setAttribute('aria-label', 'Interrompi registrazione vocale');
    } else if (supportsRecording) {
        micButton.setAttribute('aria-label', 'Avvia registrazione vocale');
    } else if (canFallback) {
        micButton.setAttribute('aria-label', 'Avvia dettatura vocale');
    } else {
        micButton.setAttribute('aria-label', 'Ricerca vocale non supportata');
    }

    if (micStatus) {
        const statusText = state.voiceError
            ? `Errore comando vocale: ${state.voiceError}`
            : state.isProcessingVoice
                ? 'Invio e trascrizione della registrazione in corso…'
                : state.isRecording
                    ? `Registrazione vocale attiva (max ${Math.round(MAX_RECORDING_DURATION_MS / 1000)} secondi).`
                    : supportsRecording || canFallback
                        ? 'Ricerca vocale pronta.'
                        : 'Ricerca vocale non supportata dal dispositivo.';
        micStatus.textContent = statusText;
    }

    const icon = micButton.querySelector('i');
    if (!icon) {
        return;
    }

    if (isBusy) {
        icon.className = 'fas fa-circle-notch fa-spin';
    } else {
        icon.className = state.isRecording ? 'fas fa-microphone-lines' : 'fas fa-microphone';
    }
}

function renderProfileCard() {
    if (!state.elements) {
        return;
    }

    const name = getProfileName();
    const avatarUrl = getProfileAvatarUrl();
    const { profileAvatarImage, profileNameLabel } = state.elements;

    if (profileAvatarImage) {
        profileAvatarImage.src = avatarUrl;
        profileAvatarImage.alt = name;
    }

    if (profileNameLabel) {
        profileNameLabel.textContent = name;
    }
}

function navigateToProfile() {
    closeMenuSheet();
    navigateClientSide(getProfileUrl());
}

function handleLogout() {
    closeMenuSheet();
    navigateClientSide(getLogoutUrl());
}

function handleOverlayClick(event) {
    const { overlay } = ensureElements();
    if (event.target === overlay) {
        closeMenuSheet();
    }
}

function focusFirstControl() {
    const { searchInput } = ensureElements();
    if (searchInput) {
        searchInput.focus({ preventScroll: true });
    }
}

function handleEscapeKey(event) {
    if (event.key === 'Escape') {
        closeMenuSheet();
    }
}

function closeMenuSheet() {
    if (!state.sheetOpen) {
        return;
    }

    const { overlay, menuButton, searchInput } = ensureElements();
    if (state.isRecording) {
        stopServerVoiceRecording();
    }
    overlay.hidden = true;
    overlay.remove();
    document.body.classList.remove(BODY_MENU_OPEN_CLASS);

    if (state.previousOverflow !== null) {
        document.body.style.overflow = state.previousOverflow;
        state.previousOverflow = null;
    }

    state.searchTerm = '';
    if (searchInput) {
        searchInput.value = '';
    }

    menuButton.setAttribute('aria-expanded', 'false');
    document.removeEventListener('keydown', handleEscapeKey, true);
    state.sheetOpen = false;
    if (menuButton.isConnected) {
        menuButton.focus({ preventScroll: true });
    }
    updateVoiceControlUi();
}

function openMenuSheet() {
    if (state.sheetOpen) {
        return;
    }

    const { overlay, sheet, menuButton } = ensureElements();

    if (!overlay.isConnected) {
        document.body.appendChild(overlay);
    }

    overlay.hidden = false;
    state.previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    document.body.classList.add(BODY_MENU_OPEN_CLASS);
    menuButton.setAttribute('aria-expanded', 'true');
    state.sheetOpen = true;
    document.addEventListener('keydown', handleEscapeKey, true);

    requestAnimationFrame(() => {
        sheet.focus({ preventScroll: true });
        focusFirstControl();
    });

    renderMenuOverlay();
}

function handleMaintenanceClick() {
    navigateClientSide(getMaintenanceUrl());
}

function navigateToHome() {
    if (state.homeLink?.href) {
        navigateClientSide(state.homeLink.href);
        return;
    }
    navigateClientSide(getHubUrl());
}

function handleSearchInput(event) {
    state.searchTerm = event.target.value;
    renderMenuOverlay();
}

function clearSearch() {
    const { searchInput } = ensureElements();
    state.searchTerm = '';
    if (searchInput) {
        searchInput.value = '';
        searchInput.focus({ preventScroll: true });
    }
    renderMenuOverlay();
}

function toggleQuickActionsEditMode() {
    state.editQuickActions = !state.editQuickActions;
    renderQuickActionsEditor();
}

function handleHighContrastToggle(event) {
    applyHighContrast(event.target.checked);
}

function applyHighContrast(enabled) {
    if (enabled) {
        document.body.classList.add(BODY_HIGH_CONTRAST_CLASS);
    } else {
        document.body.classList.remove(BODY_HIGH_CONTRAST_CLASS);
    }
    saveHighContrastPreference(enabled);
    const { highContrastToggle } = ensureElements();
    if (highContrastToggle) {
        highContrastToggle.checked = enabled;
    }
}

function buildMenuAction(item, query) {
    const action = createElement('button', 'mobile-menu-action', { type: 'button' });

    const iconWrapper = createElement('span', 'mobile-menu-icon', { 'aria-hidden': 'true' });
    const icon = createElement('i', item.iconClass || 'fas fa-circle', { 'aria-hidden': 'true' });
    iconWrapper.append(icon);

    const label = createElement('span', 'mobile-menu-label');
    highlightMatches(label, item.label, query);
    action.append(iconWrapper, label);

    if (item.isActive) {
        const activeIndicator = createElement('span', 'mobile-menu-active', { 'aria-hidden': 'true' });
        const activeIcon = createElement('i', 'fas fa-circle');
        activeIndicator.append(activeIcon);
        action.append(activeIndicator);
    }

    action.addEventListener('click', () => {
        closeMenuSheet();
        trackMenuUsage(item);
        navigateClientSide(item.href);
    });

    return action;
}

function renderNavigationList() {
    const { menuList, emptyState, navigationSection } = ensureElements();
    menuList.innerHTML = '';

    if (!state.menuItems.length) {
        emptyState.textContent = 'Nessuna voce di menu disponibile.';
        emptyState.hidden = false;
        navigationSection.classList.remove('is-searching');
        return;
    }

    const query = state.searchTerm.trim();
    const items = query
        ? state.menuItems
              .map((item) => {
                  const score = computeSearchScore(item, query);
                  return score === null ? null : { item, score };
              })
              .filter(Boolean)
              .sort((a, b) => a.score - b.score)
              .map((entry) => entry.item)
        : state.menuItems;

    if (!items.length) {
        emptyState.hidden = false;
        menuList.hidden = true;
        navigationSection.classList.add('is-searching');
        return;
    }

    emptyState.hidden = true;
    menuList.hidden = false;
    navigationSection.classList.toggle('is-searching', Boolean(query));

    items.forEach((item) => {
        const listItem = createElement('li', `mobile-menu-item depth-${Math.min(item.depth || 0, 3)}`);
        listItem.append(buildMenuAction(item, query));
        menuList.append(listItem);
    });
}

function renderRecentItems() {
    const { recentSection, recentList } = ensureElements();

    recentList.innerHTML = '';
    const query = state.searchTerm.trim();
    const hasRecents = state.recentItems.length > 0 && !query;

    recentSection.hidden = !hasRecents;
    if (!hasRecents) {
        return;
    }

    state.recentItems.forEach((recent) => {
        const current = state.menuItems.find((item) => item.href === recent.href) || recent;
        const listItem = createElement('li', 'mobile-menu-item');
        const button = buildMenuAction(current, '');
        listItem.append(button);
        recentList.append(listItem);
    });
}

function renderQuickActionsBar() {
    const { quickTray, quickTrayScroll } = ensureElements();
    quickTrayScroll.innerHTML = '';

    const quickItems = state.quickActions
        .map((href) => state.menuItems.find((item) => item.href === href))
        .filter(Boolean);

    if (!quickItems.length) {
        quickTray.hidden = true;
        return;
    }

    quickTray.hidden = false;

    quickItems.forEach((item) => {
        const button = createElement('button', 'quick-action-button', {
            type: 'button',
            'aria-label': item.label,
        });
        const icon = createElement('i', item.iconClass || 'fas fa-circle', { 'aria-hidden': 'true' });
        const label = createElement('span');
        label.textContent = item.label;
        button.append(icon, label);
        button.addEventListener('click', () => {
            trackMenuUsage(item);
            navigateClientSide(item.href);
        });
        quickTrayScroll.append(button);
    });
}

function renderQuickActionsEditor() {
    const {
        quickActionsSection,
        quickActionsSelected,
        quickActionsAvailable,
        quickActionsHint,
        quickEditButton,
    } = ensureElements();

    quickActionsSelected.innerHTML = '';
    quickActionsAvailable.innerHTML = '';

    const query = state.searchTerm.trim();
    const isVisible = !query;
    quickActionsSection.hidden = !isVisible;
    if (!isVisible) {
        return;
    }

    quickEditButton.textContent = state.editQuickActions
        ? 'Termina personalizzazione'
        : 'Personalizza azioni rapide';

    quickActionsHint.hidden = !state.editQuickActions;

    const currentQuickItems = state.quickActions
        .map((href) => state.menuItems.find((item) => item.href === href))
        .filter(Boolean);

    if (!currentQuickItems.length) {
        const empty = createElement('p', 'mobile-quick-actions-empty');
        empty.textContent = 'Aggiungi fino a quattro scorciatoie per raggiungere le funzioni chiave in un tap.';
        quickActionsSelected.append(empty);
    } else {
        currentQuickItems.forEach((item, index) => {
            const chip = createElement('div', 'mobile-quick-chip');
            const leading = createElement('button', 'mobile-quick-chip-main', {
                type: 'button',
                'aria-label': `Apri ${item.label}`,
            });
            leading.append(createElement('i', item.iconClass || 'fas fa-circle', { 'aria-hidden': 'true' }));
            const label = createElement('span');
            label.textContent = item.label;
            leading.append(label);
            leading.addEventListener('click', () => {
                trackMenuUsage(item);
                navigateClientSide(item.href);
            });

            chip.append(leading);

            if (state.editQuickActions) {
                const actions = createElement('div', 'mobile-quick-chip-actions');
                const upButton = createElement('button', 'quick-chip-move', {
                    type: 'button',
                    'aria-label': 'Sposta in alto',
                });
                upButton.append(createElement('i', 'fas fa-chevron-up', { 'aria-hidden': 'true' }));
                upButton.disabled = index === 0;
                upButton.addEventListener('click', () => moveQuickAction(index, -1));

                const downButton = createElement('button', 'quick-chip-move', {
                    type: 'button',
                    'aria-label': 'Sposta in basso',
                });
                downButton.append(createElement('i', 'fas fa-chevron-down', { 'aria-hidden': 'true' }));
                downButton.disabled = index === currentQuickItems.length - 1;
                downButton.addEventListener('click', () => moveQuickAction(index, 1));

                const removeButton = createElement('button', 'quick-chip-remove', {
                    type: 'button',
                    'aria-label': 'Rimuovi scorciatoia',
                });
                removeButton.append(createElement('i', 'fas fa-trash', { 'aria-hidden': 'true' }));
                removeButton.addEventListener('click', () => removeQuickAction(item.href));

                actions.append(upButton, downButton, removeButton);
                chip.append(actions);
            }

            quickActionsSelected.append(chip);
        });
    }

    if (!state.editQuickActions) {
        return;
    }

    const availableItems = state.menuItems.filter(
        (item) => !state.quickActions.includes(item.href),
    );

    if (!availableItems.length) {
        const empty = createElement('p', 'mobile-quick-actions-empty');
        empty.textContent = 'Hai già selezionato tutte le voci disponibili.';
        quickActionsAvailable.append(empty);
        return;
    }

    const list = createElement('div', 'mobile-quick-actions-grid');
    availableItems.forEach((item) => {
        const button = createElement('button', 'mobile-quick-add', {
            type: 'button',
            'aria-label': `Aggiungi ${item.label} alle azioni rapide`,
        });
        button.append(createElement('i', item.iconClass || 'fas fa-circle', { 'aria-hidden': 'true' }));
        const label = createElement('span');
        label.textContent = item.label;
        button.append(label);
        button.disabled = state.quickActions.length >= MAX_QUICK_ACTIONS;
        button.addEventListener('click', () => addQuickAction(item.href));
        list.append(button);
    });
    quickActionsAvailable.append(list);
}

function setQuickActions(next) {
    const unique = next.filter((href, index) => next.indexOf(href) === index).slice(0, MAX_QUICK_ACTIONS);
    state.quickActions = unique;
    saveQuickActions(unique);
    renderQuickActionsBar();
    renderQuickActionsEditor();
}

function moveQuickAction(index, offset) {
    const next = [...state.quickActions];
    const [item] = next.splice(index, 1);
    next.splice(index + offset, 0, item);
    setQuickActions(next);
}

function removeQuickAction(href) {
    const next = state.quickActions.filter((item) => item !== href);
    setQuickActions(next);
}

function addQuickAction(href) {
    if (state.quickActions.includes(href)) {
        return;
    }
    setQuickActions([...state.quickActions, href]);
}

function renderMenuOverlay() {
    renderProfileCard();
    renderQuickActionsEditor();
    renderRecentItems();
    renderNavigationList();
}

function updateHomeShortcut() {
    const { homeLabel, homeButton } = ensureElements();
    const preferredHome = state.menuItems.find((item) => HUB_LABEL_PATTERN.test(item.label))
        || state.menuItems.find((item) => DESK_LABEL_PATTERN.test(item.label))
        || state.menuItems[0]
        || null;

    state.homeLink = preferredHome;

    if (preferredHome) {
        homeLabel.textContent = preferredHome.label;
        homeButton.setAttribute('aria-label', `Vai a ${preferredHome.label}`);
        homeButton.classList.toggle('is-active', Boolean(preferredHome.isActive));
    } else {
        homeLabel.textContent = 'Home';
        homeButton.setAttribute('aria-label', 'Vai alla home');
        homeButton.classList.remove('is-active');
    }
}

function syncQuickActionsWithMenu() {
    const storedQuickActions = loadQuickActions();
    const menuMap = new Map(state.menuItems.map((item) => [item.href, item]));
    const resolved = storedQuickActions.filter((href) => menuMap.has(href));

    if (!resolved.length) {
        const defaultsFromContext = (getContext().quickActionsDefaults || []).slice(0, MAX_QUICK_ACTIONS);
        const defaults = defaultsFromContext.length
            ? defaultsFromContext
            : state.menuItems.slice(0, MAX_QUICK_ACTIONS).map((item) => item.href);
        state.quickActions = defaults;
        if (defaults.length) {
            saveQuickActions(defaults);
        }
    } else {
        if (resolved.length !== storedQuickActions.length) {
            saveQuickActions(resolved);
        }
        state.quickActions = resolved;
    }

    renderQuickActionsBar();
}

function syncRecentItemsWithMenu() {
    const storedRecents = loadRecents();
    const menuMap = new Map(state.menuItems.map((item) => [item.href, item]));
    const refreshed = storedRecents
        .map((recent) => {
            const current = menuMap.get(recent.href);
            return current
                ? { ...recent, label: current.label, iconClass: current.iconClass }
                : recent;
        })
        .slice(0, MAX_RECENTS);

    state.recentItems = refreshed;
    saveRecents(refreshed);
}

function refreshMenuItems(forceFallback = false) {
    if (!forceFallback && state.context) {
        state.menuItems = Array.isArray(state.context.navigation)
            ? state.context.navigation.map((item) => ({ ...item }))
            : [];
    } else {
        const container = document.querySelector(SIDEBAR_CONTAINER_SELECTOR);
        state.menuItems = collectSidebarMenuItems(container);
    }

    const currentPath = normalizePath(window.location.pathname);
    state.menuItems = state.menuItems.map((item) => ({
        ...item,
        isActive: normalizePath(item.href || '') === currentPath,
    }));

    if (!state.isActive) {
        return;
    }

    updateHomeShortcut();
    syncQuickActionsWithMenu();
    syncRecentItemsWithMenu();
    renderMenuOverlay();
}

function watchSidebar() {
    if (state.context) {
        return;
    }
    const container = document.querySelector(SIDEBAR_CONTAINER_SELECTOR);
    if (!container) {
        return;
    }

    if (state.sidebarObserver) {
        state.sidebarObserver.disconnect();
    }

    state.sidebarObserver = new MutationObserver(() => {
        refreshMenuItems();
    });

    state.sidebarObserver.observe(container, {
        subtree: true,
        childList: true,
        attributes: true,
        attributeFilter: ['class'],
    });

    document.addEventListener('htmx:afterSwap', refreshMenuItems);
}

function unwatchSidebar() {
    if (state.sidebarObserver) {
        state.sidebarObserver.disconnect();
        state.sidebarObserver = null;
    }
    document.removeEventListener('htmx:afterSwap', refreshMenuItems);
}

function handleMediaChange(event) {
    if (event.matches) {
        activateShell();
    } else {
        deactivateShell();
    }
}

function activateShell() {
    if (state.isActive) {
        refreshMenuItems();
        return;
    }

    const proceed = () => {
        const {
            commandBar,
            menuButton,
            fabButton,
            homeButton,
            fabAvatar,
            quickTray,
            highContrastToggle,
        } = ensureElements();

        if (fabAvatar) {
            fabAvatar.setAttribute('src', getAvatarUrl());
        }

        document.body.classList.add(BODY_ACTIVE_CLASS);

        if (menuButton) {
            menuButton.addEventListener('click', openMenuSheet);
        }
        if (fabButton) {
            fabButton.addEventListener('click', handleMaintenanceClick);
        }
        if (homeButton) {
            homeButton.addEventListener('click', navigateToHome);
        }

        const prefersHighContrast = loadHighContrastPreference();
        applyHighContrast(prefersHighContrast);
        if (highContrastToggle) {
            highContrastToggle.checked = prefersHighContrast;
        }

        renderProfileCard();
        updateVoiceControlUi();

        state.isActive = true;
        refreshMenuItems(Boolean(!state.context));
        watchSidebar();
    };

    ensureContextLoaded().then(() => {
        proceed();
    }).catch(() => {
        proceed();
    });

    if (state.contextPromise) {
        return;
    }

}

function deactivateShell() {
    if (!state.isActive) {
        return;
    }

    closeMenuSheet();
    teardownVoiceRecorder();

    const {
        commandBar,
        menuButton,
        fabButton,
        homeButton,
        quickTray,
    } = ensureElements();
    if (menuButton) {
        menuButton.removeEventListener('click', openMenuSheet);
    }
    if (fabButton) {
        fabButton.removeEventListener('click', handleMaintenanceClick);
    }
    if (homeButton) {
        homeButton.removeEventListener('click', navigateToHome);
    }

    if (commandBar && commandBar.isConnected) {
        commandBar.remove();
    }

    if (quickTray && quickTray.isConnected) {
        quickTray.remove();
    }

    document.body.classList.remove(BODY_ACTIVE_CLASS, BODY_MENU_OPEN_CLASS);

    unwatchSidebar();
    state.isActive = false;
}

function bootstrapMobileShell() {
    if (typeof window === 'undefined' || typeof document === 'undefined') {
        return;
    }

    if (!document.body?.classList?.contains('authenticated-layout')) {
        return;
    }

    state.mediaQuery = window.matchMedia(MOBILE_MEDIA_QUERY);

    if (state.mediaQuery.matches) {
        activateShell();
    }

    if (state.mediaQuery.addEventListener) {
        state.mediaQuery.addEventListener('change', handleMediaChange);
    } else if (state.mediaQuery.addListener) {
        state.mediaQuery.addListener(handleMediaChange);
    }
    window.addEventListener('pageshow', refreshMenuItems);
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bootstrapMobileShell);
} else {
    bootstrapMobileShell();
}

if (typeof window !== 'undefined') {
    window.addEventListener('popstate', () => {
        if (!state.isActive) {
            return;
        }
        navigateClientSide(window.location.href, { replace: true });
    });
}
