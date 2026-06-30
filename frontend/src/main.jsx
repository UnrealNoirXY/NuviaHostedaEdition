import React, {
    useState,
    useEffect,
    useCallback,
    useMemo,
    useRef,
} from 'react';
import ReactDOM from 'react-dom/client';
import apiClient from './apiClient';
import Dashboard from './components/Dashboard';
import Desktop from './components/Desktop';
import MobileOS from './components/MobileOS';
import BootScreen from './components/BootScreen';
import TopNav from './components/TopNav';
import WidgetGallery from './components/WidgetGallery';
import usePwaRegistration from './hooks/usePwaRegistration';
import './pwa/registration';

import 'react-grid-layout/css/styles.css';
import 'react-resizable/css/styles.css';
import './components/Dashboard.css';

const formatDateTime = (date) => {
    if (!date) {
        return 'Sincronizzazione in corso…';
    }

    try {
        return new Intl.DateTimeFormat('it-IT', {
            dateStyle: 'short',
            timeStyle: 'short',
        }).format(date);
    } catch (error) {
        console.error('Impossibile formattare la data di sincronizzazione', error);
        return date.toLocaleString();
    }
};

const FOCUS_MODE_KEY = 'homeDesk.focusMode';
const TIMESCALE_KEY = 'homeDesk.timescale';
const COMPACT_MODE_KEY = 'homeDesk.compactLayout';
const GRID_COLUMNS = { lg: 12, md: 10, sm: 6, xs: 4, xxs: 2 };
const GRID_BREAKPOINT_ORDER = ['lg', 'md', 'sm', 'xs', 'xxs'];
const MAX_ATTACHMENT_SIZE_MB = 8;
const ALLOWED_ATTACHMENT_PREFIX = 'image/';
const MAINTENANCE_DRAFT_ENDPOINT = '/api/maintenance/assistant-draft/';
const VOICE_COMMAND_TIMEOUT_MS = 12000;

const useIsMobile = () => {
    const getInitialValue = useCallback(() => {
        if (typeof window === 'undefined' || !window.matchMedia) {
            return false;
        }

        return window.matchMedia('(max-width: 767px)').matches;
    }, []);

    const [isMobile, setIsMobile] = useState(getInitialValue);

    useEffect(() => {
        if (typeof window === 'undefined' || !window.matchMedia) {
            return undefined;
        }

        const mediaQuery = window.matchMedia('(max-width: 767px)');
        const handleChange = (event) => {
            setIsMobile(event.matches);
        };

        handleChange(mediaQuery);

        if (mediaQuery.addEventListener) {
            mediaQuery.addEventListener('change', handleChange);
            return () => mediaQuery.removeEventListener('change', handleChange);
        }

        mediaQuery.addListener(handleChange);
        return () => mediaQuery.removeListener(handleChange);
    }, [getInitialValue]);

    return isMobile;
};

function App() {
    const [isBooting, setIsBooting] = useState(true);
    const [layouts, setLayouts] = useState({});
    const [openWindows, setOpenWindows] = useState([]);
    const [pinnedIcons, setPinnedIcons] = useState([]);
    const [workspaces, setWorkspaces] = useState([]);
    const [activeWorkspaceId, setActiveWorkspaceId] = useState(0);
    const [availableWidgets, setAvailableWidgets] = useState([]);
    const [availableApps, setAvailableApps] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [isSaving, setIsSaving] = useState(false);
    const [isEditable, setIsEditable] = useState(false);
    const [isGalleryOpen, setIsGalleryOpen] = useState(false);
    const [lastSyncedAt, setLastSyncedAt] = useState(null);
    const [focusMode, setFocusMode] = useState(() => {
        try {
            const stored = window.localStorage.getItem(FOCUS_MODE_KEY);
            return stored ? JSON.parse(stored) : false;
        } catch (err) {
            console.warn('Impossibile leggere la preferenza focus mode', err);
            return false;
        }
    });
    const [timescale, setTimescale] = useState(() => {
        try {
            const stored = window.localStorage.getItem(TIMESCALE_KEY);
            return stored ? JSON.parse(stored) : 'oggi';
        } catch (err) {
            console.warn('Impossibile leggere la preferenza timescale', err);
            return 'oggi';
        }
    });
    const [compactLayout, setCompactLayout] = useState(() => {
        try {
            const stored = window.localStorage.getItem(COMPACT_MODE_KEY);
            return stored ? JSON.parse(stored) : false;
        } catch (err) {
            console.warn('Impossibile leggere la preferenza layout compatto', err);
            return false;
        }
    });
    const [assistantOpen, setAssistantOpen] = useState(false);
    const [assistantStep, setAssistantStep] = useState(0);
    const [assistantData, setAssistantData] = useState({
        area: '',
        priority: 'standard',
        notes: '',
        assetCode: '',
        attachmentFile: null,
        attachmentPreviewUrl: '',
        attachmentName: '',
    });
    const [assistantFileError, setAssistantFileError] = useState('');
    const [assistantDraftError, setAssistantDraftError] = useState('');
    const [isSubmittingDraft, setIsSubmittingDraft] = useState(false);
    const [timelineFilter, setTimelineFilter] = useState('all');
    const [voiceCommandState, setVoiceCommandState] = useState('idle');
    const [voiceCommandMessage, setVoiceCommandMessage] = useState('Comando vocale pronto.');

    const isMobile = useIsMobile();
    usePwaRegistration();

    useEffect(() => {
        const body = document.body;
        if (!body) {
            return undefined;
        }

        const shouldLock = isGalleryOpen || assistantOpen;

        if (shouldLock) {
            body.classList.add('is-overlay-locked', 'has-desk-overlay');
        } else {
            body.classList.remove('is-overlay-locked', 'has-desk-overlay');
        }

        return () => {
            body.classList.remove('is-overlay-locked', 'has-desk-overlay');
        };
    }, [assistantOpen, isGalleryOpen]);

    const MAINTENANCE_REQUEST_URL = '/maintenance/ticket/nuovo/';
    const speechRecognitionClass = useMemo(
        () => (typeof window !== 'undefined'
            ? window.SpeechRecognition || window.webkitSpeechRecognition || null
            : null),
        [],
    );
    const recognitionRef = useRef(null);
    const voiceTimeoutRef = useRef(null);
    const voiceButtonRef = useRef(null);
    const voiceCommandStateRef = useRef('idle');
    const setVoiceState = useCallback((nextState) => {
        voiceCommandStateRef.current = nextState;
        setVoiceCommandState(nextState);
    }, []);

    const handleOpenMaintenanceRequest = useCallback(() => {
        window.location.assign(MAINTENANCE_REQUEST_URL);
    }, []);

    const assistantStepLabels = useMemo(() => ['Asset', 'Priorità', 'Dettagli'], []);

    const handleAssistantOpen = useCallback(() => {
        setAssistantDraftError('');
        setAssistantFileError('');
        setAssistantOpen(true);
        setAssistantStep(0);
    }, []);

    useEffect(() => {
        const handler = () => {
            handleAssistantOpen();
        };
        document.addEventListener('homeDesk.openAssistant', handler);
        return () => {
            document.removeEventListener('homeDesk.openAssistant', handler);
        };
    }, [handleAssistantOpen]);

    const focusVoiceButton = useCallback(() => {
        if (voiceButtonRef.current) {
            voiceButtonRef.current.focus({ preventScroll: true });
        }
    }, []);

    const clearVoiceTimeout = useCallback(() => {
        if (voiceTimeoutRef.current) {
            clearTimeout(voiceTimeoutRef.current);
            voiceTimeoutRef.current = null;
        }
    }, []);

    const stopVoiceRecognition = useCallback(() => {
        clearVoiceTimeout();
        if (!recognitionRef.current) {
            return;
        }
        try {
            recognitionRef.current.stop();
        } catch (error) {
            console.warn('Impossibile fermare la dettatura vocale', error);
        }
    }, [clearVoiceTimeout]);

    const handleVoiceCommandAction = useCallback((transcript) => {
        const normalized = (transcript || '').toLocaleLowerCase('it-IT');
        if (!normalized) {
            setVoiceState('error');
            setVoiceCommandMessage('Nessun comando rilevato. Riprova.');
            focusVoiceButton();
            return;
        }

        if (normalized.includes('manutenz') || normalized.includes('assistente')) {
            setVoiceCommandMessage('Apro l’assistente manutenzione.');
            setVoiceState('idle');
            handleAssistantOpen();
            return;
        }

        if (normalized.includes('widget')) {
            setVoiceCommandMessage('Apro la libreria widget.');
            setVoiceState('idle');
            setIsGalleryOpen(true);
            setIsEditable(true);
            return;
        }

        if (normalized.includes('focus')) {
            setVoiceCommandMessage('Attivo/disattivo la modalità focus.');
            setVoiceState('idle');
            setFocusMode((prev) => !prev);
            return;
        }

        setVoiceState('error');
        setVoiceCommandMessage(`Comando non riconosciuto: "${transcript}".`);
        focusVoiceButton();
    }, [focusVoiceButton, handleAssistantOpen, setFocusMode, setIsEditable, setIsGalleryOpen]);

    const startVoiceCommand = useCallback(() => {
        if (!speechRecognitionClass) {
            setVoiceState('error');
            setVoiceCommandMessage('Comando vocale non supportato su questo dispositivo.');
            focusVoiceButton();
            return;
        }

        if (voiceCommandState === 'recording') {
            stopVoiceRecognition();
            setVoiceState('processing');
            setVoiceCommandMessage('Elaborazione del comando…');
            return;
        }

        clearVoiceTimeout();
        setVoiceState('recording');
        setVoiceCommandMessage('Ascolto attivo. Pronuncia un comando per la Home Desk.');

        if (!recognitionRef.current) {
            recognitionRef.current = new speechRecognitionClass();
            recognitionRef.current.lang = 'it-IT';
            recognitionRef.current.interimResults = false;
            recognitionRef.current.maxAlternatives = 1;
        }

        recognitionRef.current.onresult = (event) => {
            clearVoiceTimeout();
            const transcript = event?.results?.[0]?.[0]?.transcript;
            setVoiceState('processing');
            setVoiceCommandMessage(transcript ? `Comando rilevato: "${transcript}".` : 'Nessun comando rilevato.');
            handleVoiceCommandAction(transcript);
        };

        recognitionRef.current.onerror = (event) => {
            clearVoiceTimeout();
            setVoiceState('error');
            setVoiceCommandMessage(event?.error ? `Errore microfono: ${event.error}` : 'Errore durante la dettatura vocale.');
            focusVoiceButton();
        };

        recognitionRef.current.onend = () => {
            if (voiceCommandStateRef.current === 'recording') {
                setVoiceState('error');
                setVoiceCommandMessage('Tempo di ascolto scaduto.');
                focusVoiceButton();
            }
            clearVoiceTimeout();
        };

        voiceTimeoutRef.current = setTimeout(() => {
            if (voiceCommandStateRef.current === 'recording') {
                stopVoiceRecognition();
                setVoiceState('error');
                setVoiceCommandMessage('Tempo massimo di ascolto raggiunto.');
                focusVoiceButton();
            }
        }, VOICE_COMMAND_TIMEOUT_MS);

        try {
            recognitionRef.current.start();
        } catch (error) {
            console.error('Impossibile avviare la dettatura vocale', error);
            setVoiceState('error');
            setVoiceCommandMessage('Non è stato possibile avviare il microfono. Riprova.');
            focusVoiceButton();
        }
    }, [clearVoiceTimeout, focusVoiceButton, handleVoiceCommandAction, speechRecognitionClass, stopVoiceRecognition, voiceCommandState]);

    const handleAssistantClose = useCallback(() => {
        setAssistantOpen(false);
        setAssistantStep(0);
        setIsSubmittingDraft(false);
    }, []);

    useEffect(() => {
        voiceCommandStateRef.current = voiceCommandState;
    }, [voiceCommandState]);

    const handleAssistantChange = useCallback((field, value) => {
        setAssistantData((prev) => ({
            ...prev,
            [field]: value,
        }));
    }, []);

    const handleAssistantFileChange = useCallback((event) => {
        const file = event.target.files?.[0];
        const input = event.target;

        if (!file) {
            setAssistantData((prev) => ({
                ...prev,
                attachmentFile: null,
                attachmentPreviewUrl: '',
                attachmentName: '',
            }));
            setAssistantFileError('');
            return;
        }

        const hasAllowedType = file.type && file.type.startsWith(ALLOWED_ATTACHMENT_PREFIX);
        const maxSizeBytes = MAX_ATTACHMENT_SIZE_MB * 1024 * 1024;

        if (!hasAllowedType) {
            setAssistantFileError('Carica solo immagini (JPG, PNG, HEIC o WEBP).');
            setAssistantData((prev) => ({
                ...prev,
                attachmentFile: null,
                attachmentPreviewUrl: '',
                attachmentName: '',
            }));
            if (input) {
                input.value = '';
            }
            return;
        }

        if (file.size > maxSizeBytes) {
            setAssistantFileError(`Il file è troppo grande. Dimensione massima: ${MAX_ATTACHMENT_SIZE_MB} MB.`);
            setAssistantData((prev) => ({
                ...prev,
                attachmentFile: null,
                attachmentPreviewUrl: '',
                attachmentName: '',
            }));
            if (input) {
                input.value = '';
            }
            return;
        }

        const previewUrl = URL.createObjectURL(file);
        setAssistantFileError('');
        setAssistantData((prev) => {
            if (prev.attachmentPreviewUrl) {
                URL.revokeObjectURL(prev.attachmentPreviewUrl);
            }
            return {
                ...prev,
                attachmentFile: file,
                attachmentPreviewUrl: previewUrl,
                attachmentName: file.name,
            };
        });
    }, []);

    const handleAssistantResetAttachment = useCallback(() => {
        setAssistantData((prev) => ({
            ...prev,
            attachmentFile: null,
            attachmentPreviewUrl: '',
            attachmentName: '',
        }));
        setAssistantFileError('');
    }, []);

    const finalizeAssistant = useCallback(async () => {
        setAssistantDraftError('');
        setIsSubmittingDraft(true);

        const formData = new FormData();
        formData.append('area', assistantData.area || '');
        formData.append('priority', assistantData.priority || '');
        formData.append('note', assistantData.notes || '');
        formData.append('asset', assistantData.assetCode || '');

        if (assistantData.attachmentFile) {
            formData.append('attachment', assistantData.attachmentFile, assistantData.attachmentName || assistantData.attachmentFile.name);
        }

        try {
            const response = await apiClient.post(MAINTENANCE_DRAFT_ENDPOINT, formData, {
                headers: {
                    'Content-Type': 'multipart/form-data',
                },
            });

            const draftId = response?.data?.draft_id
                || response?.data?.draftId
                || response?.data?.id
                || response?.data?.token
                || response?.data?.draftToken;
            const redirectUrl = response?.data?.redirect_url || response?.data?.redirectUrl;

            handleAssistantClose();

            if (redirectUrl) {
                window.location.assign(redirectUrl);
                return;
            }

            if (!draftId) {
                throw new Error('Draft ID mancante nella risposta');
            }

            window.location.assign(`${MAINTENANCE_REQUEST_URL}?draft=${encodeURIComponent(draftId)}`);
        } catch (draftError) {
            console.error('Errore durante la creazione del draft manutenzione', draftError);
            setAssistantDraftError('Non è stato possibile preparare la richiesta. Verifica la connessione e riprova.');
        } finally {
            setIsSubmittingDraft(false);
        }
    }, [assistantData, handleAssistantClose]);

    const handleAssistantNext = useCallback(async () => {
        if (assistantStep < assistantStepLabels.length - 1) {
            setAssistantStep((prev) => prev + 1);
            return;
        }
        if (isSubmittingDraft) {
            return;
        }
        await finalizeAssistant();
    }, [assistantStep, assistantStepLabels, finalizeAssistant, isSubmittingDraft]);

    const handleAssistantBack = useCallback(() => {
        setAssistantStep((prev) => Math.max(prev - 1, 0));
    }, []);

    const assistantStepIsValid = useMemo(() => {
        if (assistantStep === 0) {
            return Boolean(assistantData.area || assistantData.assetCode);
        }
        if (assistantStep === 1) {
            return Boolean(assistantData.priority);
        }
        return true;
    }, [assistantData.area, assistantData.assetCode, assistantData.priority, assistantStep]);

    useEffect(() => {
        document.title = 'Nuvia Home Desk';
    }, []);

    useEffect(() => () => {
        if (assistantData.attachmentPreviewUrl) {
            URL.revokeObjectURL(assistantData.attachmentPreviewUrl);
        }
    }, [assistantData.attachmentPreviewUrl]);

    useEffect(() => {
        apiClient.get('/api/desk/layout/')
            .then((response) => {
                setLayouts(response.data.layouts);
                setOpenWindows(response.data.open_windows || []);
                setPinnedIcons(response.data.pinned_icons || []);
                setWorkspaces(response.data.workspaces || [{ id: 0, name: 'Principale' }]);
                setActiveWorkspaceId(response.data.active_workspace_id || 0);
                setAvailableWidgets(response.data.available_widgets);
                setAvailableApps(response.data.available_apps || []);
                setLastSyncedAt(new Date());
                setLoading(false);
            })
            .catch((err) => {
                console.error('Error fetching layout:', err);
                setError('Impossibile caricare la configurazione della desk.');
                setLoading(false);
            });
    }, []);

    const handleLayoutsChange = useCallback((newLayouts) => {
        setLayouts((previousLayouts) => ({
            ...previousLayouts,
            ...newLayouts,
        }));
    }, []);

    const handleRemoveWidget = useCallback((widgetId) => {
        setLayouts((previousLayouts) => {
            let hasChanges = false;
            const updatedLayouts = Object.keys(previousLayouts).reduce((accumulator, breakpoint) => {
                const layoutForBreakpoint = Array.isArray(previousLayouts[breakpoint]) ? previousLayouts[breakpoint] : [];
                const filteredLayout = layoutForBreakpoint.filter((widget) => widget.i !== widgetId);
                if (filteredLayout.length !== layoutForBreakpoint.length) {
                    hasChanges = true;
                }
                accumulator[breakpoint] = filteredLayout;
                return accumulator;
            }, {});
            return hasChanges ? updatedLayouts : previousLayouts;
        });
    }, []);

    const handleAddWidget = useCallback((widgetId) => {
        const widgetToAdd = availableWidgets.find((widget) => widget.id === widgetId);
        if (!widgetToAdd) {
            return;
        }

        let widgetAdded = false;
        setLayouts((previousLayouts) => {
            const layoutAlreadyContainsWidget = Object.values(previousLayouts).some(
                (layout) => Array.isArray(layout) && layout.some((item) => item.i === widgetId),
            );

            if (layoutAlreadyContainsWidget) {
                return previousLayouts;
            }

            const nextLayouts = { ...previousLayouts };

            GRID_BREAKPOINT_ORDER.forEach((breakpoint) => {
                const currentLayout = Array.isArray(nextLayouts[breakpoint]) ? [...nextLayouts[breakpoint]] : [];
                const isFullWidthBreakpoint = ['sm', 'xs', 'xxs'].includes(breakpoint);
                const baseWidth = widgetToAdd.w || GRID_COLUMNS[breakpoint] || 4;
                const width = isFullWidthBreakpoint
                    ? GRID_COLUMNS[breakpoint]
                    : Math.min(baseWidth, GRID_COLUMNS[breakpoint] || baseWidth);

                currentLayout.push({
                    i: widgetToAdd.id,
                    x: 0,
                    y: Infinity,
                    w: width,
                    h: widgetToAdd.h || 4,
                });
                nextLayouts[breakpoint] = currentLayout;
            });

            widgetAdded = true;
            return nextLayouts;
        });

        if (widgetAdded) {
            setIsGalleryOpen(false);
        }
    }, [availableWidgets]);

    const handleSaveLayout = () => {
        setIsSaving(true);
        apiClient.post('/api/desk/layout/', { layout: layouts })
            .then(() => {
                setIsSaving(false);
                setIsEditable(false);
                setLastSyncedAt(new Date());
            })
            .catch((err) => {
                console.error('Error saving layout:', err);
                setError('Errore durante il salvataggio del layout.');
                setIsSaving(false);
            });
    };

    const totalWidgets = useMemo(() => (layouts.lg ? layouts.lg.length : 0), [layouts]);
    const lastSyncedLabel = useMemo(() => formatDateTime(lastSyncedAt), [lastSyncedAt]);
    const timescaleLabel = useMemo(() => {
        switch (timescale) {
            case 'settimana':
                return 'Ultimi 7 giorni';
            case 'mese':
                return 'Ultimi 30 giorni';
            case 'oggi':
            default:
                return 'Oggi';
        }
    }, [timescale]);

    const focusDescription = focusMode
        ? 'Modalità focus attiva: vengono evidenziati solo i KPI critici e le notifiche prioritarie.'
        : 'Modalità standard: visualizzi l’intera plancia con tutti i widget e le metriche disponibili.';

    const timelineEvents = useMemo(() => {
        const events = [];

        events.push({
            id: 'sync-status',
            category: 'sistema',
            title: 'Sincronizzazione completata',
            timestamp: lastSyncedAt ? lastSyncedAt.getTime() : null,
            description: lastSyncedAt
                ? `Layout aggiornato alle ${lastSyncedLabel}`
                : 'Salva il layout per iniziare a tracciare gli aggiornamenti.',
            icon: 'fa-cloud-arrow-down',
            action: {
                label: isEditable ? 'Blocca layout' : 'Modifica layout',
                onClick: () => setIsEditable((prev) => !prev),
            },
        });

        events.push({
            id: 'widgets-library',
            category: 'dashboard',
            title: `${totalWidgets} widget attivi`,
            description: 'Arricchisci la dashboard con viste personalizzate e micro-interazioni.',
            icon: 'fa-table-cells-large',
            action: {
                label: 'Aggiungi widget',
                onClick: () => setIsGalleryOpen(true),
            },
        });

        events.push({
            id: 'maintenance-shortcut',
            category: 'manutenzione',
            title: 'Richiesta rapida di manutenzione',
            description: 'Apri il modulo precompilato con il wizard mobile ottimizzato.',
            icon: 'fa-screwdriver-wrench',
            action: {
                label: 'Avvia assistente',
                onClick: handleAssistantOpen,
            },
        });

        events.push({
            id: 'focus-mode',
            category: 'dashboard',
            title: focusMode ? 'Focus mode attiva' : 'Focus mode disattivata',
            description: focusMode
                ? 'Sono in evidenza i KPI critici e gli alert di priorità alta.'
                : 'Attiva la modalità focus per isolare gli indicatori urgenti.',
            icon: focusMode ? 'fa-fire' : 'fa-eye',
            action: {
                label: focusMode ? 'Mostra tutto' : 'Evidenzia KPI',
                onClick: () => setFocusMode((prev) => !prev),
            },
        });

        return events;
    }, [focusMode, handleAssistantOpen, isEditable, lastSyncedAt, lastSyncedLabel, setFocusMode, setIsEditable, setIsGalleryOpen, totalWidgets]);

    const filteredTimeline = useMemo(() => {
        if (timelineFilter === 'all') {
            return timelineEvents;
        }
        return timelineEvents.filter((event) => event.category === timelineFilter);
    }, [timelineEvents, timelineFilter]);

    const timelineCategories = useMemo(
        () => [
            { id: 'all', label: 'Tutto' },
            { id: 'manutenzione', label: 'Manutenzione' },
            { id: 'dashboard', label: 'Dashboard' },
            { id: 'sistema', label: 'Sistema' },
        ],
        [],
    );

    const inboxItems = useMemo(
        () => [
            { id: 'alerts', label: 'Alert critici', count: focusMode ? 2 : 1, icon: 'fa-triangle-exclamation', tone: 'danger' },
            { id: 'chat', label: 'Chat aperte', count: 3, icon: 'fa-comments', tone: 'info' },
            { id: 'approvals', label: 'Approvazioni', count: 1, icon: 'fa-clipboard-check', tone: 'success' },
        ],
        [focusMode],
    );

    useEffect(() => {
        try {
            window.localStorage.setItem(FOCUS_MODE_KEY, JSON.stringify(focusMode));
        } catch (err) {
            console.warn('Impossibile salvare la preferenza focus mode', err);
        }
    }, [focusMode]);

    useEffect(() => {
        try {
            window.localStorage.setItem(TIMESCALE_KEY, JSON.stringify(timescale));
        } catch (err) {
            console.warn('Impossibile salvare la preferenza timescale', err);
        }
    }, [timescale]);

    useEffect(() => {
        try {
            window.localStorage.setItem(COMPACT_MODE_KEY, JSON.stringify(compactLayout));
        } catch (err) {
            console.warn('Impossibile salvare la preferenza layout compatto', err);
        }
    }, [compactLayout]);

    useEffect(() => {
        if (!assistantOpen) {
            return undefined;
        }

        const previousOverflow = document.body.style.overflow;
        document.body.style.overflow = 'hidden';

        const handleKeyDown = (event) => {
            if (event.key === 'Escape') {
                handleAssistantClose();
            }
        };

        document.addEventListener('keydown', handleKeyDown);

        return () => {
            document.body.style.overflow = previousOverflow;
            document.removeEventListener('keydown', handleKeyDown);
        };
    }, [assistantOpen, handleAssistantClose]);

    useEffect(() => () => {
        clearVoiceTimeout();
        if (recognitionRef.current) {
            recognitionRef.current.onresult = null;
            recognitionRef.current.onerror = null;
            recognitionRef.current.onend = null;
            try {
                recognitionRef.current.stop();
            } catch (error) {
                console.warn('Errore durante lo stop del riconoscimento vocale', error);
            }
        }
    }, [clearVoiceTimeout]);

    if (loading) {
        return (
            <div className="desk-loading-state">
                <img src="/static/img/logo.png" style={{ width: '60px', filter: 'brightness(0) invert(1)', marginBottom: '1rem' }} />
                <i className="fas fa-circle-notch fa-spin fa-2x" aria-hidden="true"></i>
                <p style={{ marginTop: '1rem', letterSpacing: '0.1em' }}>Sincronizzazione Nuvia OS…</p>
            </div>
        );
    }

    if (error) {
        return (
            <div className="desk-error-state" role="alert">
                <i className="fas fa-circle-exclamation fa-3x" aria-hidden="true"></i>
                <p style={{ marginTop: '1rem' }}>{error}</p>
                <button className="btn btn-outline-light mt-3" onClick={() => window.location.reload()}>Riprova</button>
            </div>
        );
    }

    const currentWidgetIds = layouts.lg ? layouts.lg.map((widget) => widget.i) : [];

    if (isBooting) {
        return <BootScreen onComplete={() => setIsBooting(false)} />;
    }

    if (isMobile) {
        return (
            <MobileOS
                availableWidgets={availableWidgets}
                availableApps={availableApps}
                onLaunch={(id) => {
                    const item = [...availableApps, ...availableWidgets].find(i => i.id === id);
                    if (item && item.url) window.location.assign(item.url);
                }}
            />
        );
    }

    return (
        <div
            className={`desk-shell ${isEditable ? 'desk-shell-editing' : ''} ${focusMode ? 'desk-shell-focus' : ''} ${compactLayout ? 'desk-shell-compact' : ''}`}
            data-timescale={timescale}
            data-device="desktop"
        >
                {isGalleryOpen && (
                    <WidgetGallery
                        availableWidgets={availableWidgets}
                        currentWidgetIds={currentWidgetIds}
                        onAddWidget={handleAddWidget}
                        onClose={() => setIsGalleryOpen(false)}
                    />
                )}

            <main className="desk-main desktop-mode" role="main">
                <Desktop
                    layouts={layouts}
                    initialOpenWindows={openWindows}
                    initialPinnedIcons={pinnedIcons}
                    initialWorkspaces={workspaces}
                    initialActiveWorkspaceId={activeWorkspaceId}
                    availableWidgets={availableWidgets}
                    availableApps={availableApps}
                    onLayoutChange={handleLayoutsChange}
                    onAddWidget={handleAddWidget}
                    isGalleryOpen={isGalleryOpen}
                    setIsGalleryOpen={setIsGalleryOpen}
                />
            </main>
            {assistantOpen && (
                <div className="desk-assistant-overlay" role="dialog" aria-modal="true" aria-labelledby="maintenance-assistant-title">
                    <div className="desk-assistant-panel">
                        <header className="desk-assistant-header">
                            <div>
                                <p className="desk-assistant-eyebrow">Assistente manutenzione</p>
                                <h2 id="maintenance-assistant-title">{assistantStepLabels[assistantStep]}</h2>
                            </div>
                            <button
                                type="button"
                                className="btn btn-sm btn-outline-light"
                                onClick={handleAssistantClose}
                            >
                                <i className="fas fa-xmark" aria-hidden="true"></i>
                                <span className="visually-hidden">Chiudi assistente</span>
                            </button>
                        </header>
                        <div className="desk-assistant-steps" aria-hidden="true">
                            {assistantStepLabels.map((label, index) => (
                                <div
                                    key={label}
                                    className={`desk-assistant-step ${index === assistantStep ? 'is-active' : ''} ${index < assistantStep ? 'is-complete' : ''}`}
                                >
                                    <span className="desk-assistant-step-index">{index + 1}</span>
                                    <span className="desk-assistant-step-label">{label}</span>
                                </div>
                            ))}
                        </div>
                        <div className="desk-assistant-body">
                            {assistantStep === 0 && (
                                <div className="desk-assistant-section">
                                    <p className="desk-assistant-subtitle">Quale asset richiede l&apos;intervento?</p>
                                    <div className="desk-assistant-options">
                                        {['Camere', 'Aree comuni', 'Esterni', 'Back office'].map((area) => (
                                            <button
                                                key={area}
                                                type="button"
                                                className={`desk-assistant-option ${assistantData.area === area ? 'is-selected' : ''}`}
                                                onClick={() => handleAssistantChange('area', area)}
                                            >
                                                {area}
                                            </button>
                                        ))}
                                    </div>
                                    <label className="desk-assistant-field">
                                        <span>Codice o numero asset</span>
                                        <input
                                            type="text"
                                            value={assistantData.assetCode}
                                            onChange={(event) => handleAssistantChange('assetCode', event.target.value)}
                                            placeholder="es. CAM-204 o QR"
                                        />
                                    </label>
                                    <label className="desk-assistant-field desk-assistant-upload">
                                        <span>Scanner QR / Foto</span>
                                        <input
                                            type="file"
                                            accept="image/*"
                                            capture="environment"
                                            onChange={handleAssistantFileChange}
                                        />
                                        <i className="fas fa-camera" aria-hidden="true"></i>
                                        <span>
                                            {assistantData.attachmentName
                                                ? `Allegato: ${assistantData.attachmentName}`
                                                : 'Scatta o carica un riferimento visivo'}
                                        </span>
                                    </label>
                                    <p className="text-muted mt-2">
                                        Solo immagini (max {MAX_ATTACHMENT_SIZE_MB} MB). JPG, PNG, HEIC o WEBP sono supportati.
                                    </p>
                                    {assistantFileError && (
                                        <p className="text-danger mt-1" role="alert">{assistantFileError}</p>
                                    )}
                                    {assistantData.attachmentPreviewUrl && (
                                        <div className="desk-assistant-preview">
                                            <img src={assistantData.attachmentPreviewUrl} alt="Anteprima asset" />
                                            <button
                                                type="button"
                                                className="btn btn-sm btn-outline-light"
                                                onClick={handleAssistantResetAttachment}
                                            >
                                                Rimuovi allegato
                                            </button>
                                        </div>
                                    )}
                                </div>
                            )}
                            {assistantStep === 1 && (
                                <div className="desk-assistant-section">
                                    <p className="desk-assistant-subtitle">Imposta la priorità</p>
                                    <div className="desk-assistant-options desk-assistant-options-grid">
                                        {[
                                            { id: 'critica', label: 'Critica', description: 'Intervento immediato', icon: 'fa-bolt' },
                                            { id: 'standard', label: 'Standard', description: 'Entro 24 ore', icon: 'fa-gauge-high' },
                                            { id: 'programmata', label: 'Programmato', description: 'Pianifica la finestra utile', icon: 'fa-calendar-check' },
                                        ].map((option) => (
                                            <button
                                                key={option.id}
                                                type="button"
                                                className={`desk-assistant-option ${assistantData.priority === option.id ? 'is-selected' : ''}`}
                                                onClick={() => handleAssistantChange('priority', option.id)}
                                            >
                                                <i className={`fas ${option.icon}`} aria-hidden="true"></i>
                                                <span className="desk-assistant-option-title">{option.label}</span>
                                                <span className="desk-assistant-option-description">{option.description}</span>
                                            </button>
                                        ))}
                                    </div>
                                </div>
                            )}
                            {assistantStep === 2 && (
                                <div className="desk-assistant-section">
                                    <p className="desk-assistant-subtitle">Dettagli finali</p>
                                    <label className="desk-assistant-field">
                                        <span>Note operative</span>
                                        <textarea
                                            rows={4}
                                            value={assistantData.notes}
                                            onChange={(event) => handleAssistantChange('notes', event.target.value)}
                                            placeholder="Descrivi il problema, le disponibilità e i materiali necessari"
                                        />
                                    </label>
                                    <div className="desk-assistant-summary">
                                        <h3>Riepilogo</h3>
                                        <ul>
                                            <li>
                                                <span>Asset</span>
                                                <strong>{assistantData.area || 'Non specificato'}</strong>
                                            </li>
                                            <li>
                                                <span>Codice</span>
                                                <strong>{assistantData.assetCode || '—'}</strong>
                                            </li>
                                            <li>
                                                <span>Priorità</span>
                                                <strong>{assistantData.priority}</strong>
                                            </li>
                                            <li>
                                                <span>Allegato</span>
                                                <strong>{assistantData.attachmentName || 'Nessuno'}</strong>
                                            </li>
                                        </ul>
                                    </div>
                                </div>
                            )}
                        </div>
                        {assistantDraftError && (
                            <div className="alert alert-danger mt-3" role="alert">
                                {assistantDraftError}
                            </div>
                        )}
                        <footer className="desk-assistant-actions">
                            <button type="button" className="btn btn-outline-light" onClick={handleAssistantClose}>
                                Annulla
                            </button>
                            {assistantStep > 0 && (
                                <button type="button" className="btn btn-outline-light" onClick={handleAssistantBack}>
                                    Indietro
                                </button>
                            )}
                            <button
                                type="button"
                                className="btn btn-primary desk-control-accent"
                                onClick={handleAssistantNext}
                                disabled={!assistantStepIsValid || isSubmittingDraft}
                            >
                                {assistantStep === assistantStepLabels.length - 1
                                    ? (isSubmittingDraft ? 'Invio in corso…' : 'Invia richiesta')
                                    : 'Avanti'}
                            </button>
                        </footer>
                    </div>
                </div>
            )}
        </div>
    );
}

const rootElement = document.getElementById('root');

if (rootElement) {
    const root = ReactDOM.createRoot(rootElement);
    root.render(
        <React.StrictMode>
            <App />
        </React.StrictMode>,
    );
} else {
    console.error("Elemento radice 'root' non trovato. L'app Home Desk non può essere montata.");
}
